---
name: phylo-builder
description: 'Execute the phylogenetics-agent main workflow (align -> trim -> model_select -> tree -> render) as 5 independently checkpointed bash stages, derived from the MLTree-main Nextflow pipeline. Each stage writes $RUN_DIR/checkpoints/<stage>.done.json on success; re-invocation resumes from the first incomplete stage instead of re-running from scratch. Aligner (muscle/mafft) and tree tool (raxml-ng/iqtree) are swappable per-run. Triggers: "run the phylogenetics pipeline", "build the tree", "resume tree build", "phylo-builder".'
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "run the phylogenetics pipeline"
  - "build the tree"
  - "resume tree build"
  - "phylo-builder"
  - "align and build a tree"
disable-model-invocation: true
---

# phylo-builder

> **v1.0.0.** The main-workflow phase of `phylogenetics-agent`. Unlike MLTree-main's single Nextflow DAG (all-or-nothing, no resume), this sub-skill runs each stage as a discrete bash step and checkpoints after every one — a stage that already has a valid checkpoint is skipped, not re-run.

## 0. Inputs / Outputs contract

### Inputs (consumed)

| Path | Source | Required? |
| --- | --- | --- |
| `$RUN_DIR/params.json` | `preflight/phylo-preflight` | yes |
| `$RUN_DIR/preflight.md` (verdict ≥ GO-WITH-WARNINGS) | `preflight/phylo-preflight` | yes |

### Outputs (produced)

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/checkpoints/align.done.json` | JSON | stage metadata (tool, args, output path, sha256, wall time) |
| `$RUN_DIR/checkpoints/trim.done.json` | JSON | ditto |
| `$RUN_DIR/checkpoints/model_select.done.json` | JSON | ditto (skipped/empty if `tree_tool=iqtree` or `model` was explicit) |
| `$RUN_DIR/checkpoints/tree.done.json` | JSON | ditto |
| `$RUN_DIR/checkpoints/render.done.json` | JSON | ditto |
| `$RUN_DIR/alignment/*.fasta` | FASTA | aligned sequences |
| `$RUN_DIR/trimal/*_trimal.fasta` `.html` | FASTA/HTML | trimmed alignment + trimAl report |
| `$RUN_DIR/modeltest/*.out` | text | modeltest-ng log (raxml branch only, when model not given) |
| `$RUN_DIR/trees/*` | various | `.raxml.*` or `.treefile`/`.iqtree`/`.log`, plus `.tree.txt` (gotree ASCII render) |

### Verdict gate

`qc/phylo-qc` refuses to run unless `checkpoints/render.done.json` exists.

## 0.5 Ask-User Stop Points

### SP1 — A checkpoint exists but its declared inputs changed

| Trigger | Evidence | Action |
| --- | --- | --- |
| `checkpoints/<stage>.done.json` exists, but the upstream file it was computed from (e.g. the aligner output for `trim`) has a different sha256 than what the checkpoint recorded | Stale checkpoint — re-running downstream stages on it would silently use outdated data | Ask: "The `<stage>` checkpoint's input file changed since it ran. Pick: (A) invalidate and re-run `<stage>` onward (recommended), (B) keep the stale checkpoint anyway (not recommended), (C) abort" |

**Auto-pick when**: every checkpoint's recorded input sha256 matches the current file. Default: resume from first stage without a valid checkpoint.

### SP2 — Mid-pipeline tool/method swap requested

| Trigger | Evidence | Action |
| --- | --- | --- |
| User asks to switch `aligner` or `tree_tool` after `align.done.json` (or `trim.done.json`) already exists | The swap point determines how much gets invalidated | Ask: "Switching `aligner` invalidates `align` onward (re-runs align/trim/model_select/tree/render). Switching `tree_tool` only invalidates `model_select`/`tree`/`render` (alignment + trim stay). Pick: (A) proceed and invalidate the affected checkpoints, (B) keep current tool, (C) abort" |

**Auto-pick when**: no tool/method change requested. No ask.

### SP3 — `raxml-ng --model` value is empty after modeltest-ng

| Trigger | Evidence | Action |
| --- | --- | --- |
| `modeltest-ng` output parses to an empty model string (mirrors the exact failure MLTree-main's `raxml_tree` process guards against) | modeltest-ng's `.out` format changed, or the AICc/BIC block wasn't found | Ask: "Could not extract a model from modeltest-ng output. Pick: (A) inspect `modeltest/*.out` and give the model manually (e.g. `GTR+G+I`), (B) retry modeltest-ng with `--force`, (C) switch to `tree_tool=iqtree` (built-in ModelFinder, no separate model-selection stage), (D) abort" |

**Auto-pick when**: modeltest-ng returns a non-empty model. No ask.

### Operating rule

Evidence + Recommend + Options. Auto-pick when the evidence is unambiguous.

## Prerequisites

- pixi env from `$RUN_DIR/pixi.toml` (or the phylogenetics-agent skill's own `pixi.toml`), with the tools needed for the chosen `aligner`/`tree_tool`.
- `$RUN_DIR/params.json` with verdict ≥ `GO-WITH-WARNINGS`.

## Procedure — 5 checkpointed stages

Before running any stage, compute which stages already have a **valid** checkpoint (see SP1) and skip straight to the first invalid/missing one. Each stage below is a direct bash-recipe translation of the corresponding MLTree-main process (`main.nf`), with a checkpoint write appended.

```bash
run_dir="$RUN_DIR"
ckpt="$run_dir/checkpoints"
mkdir -p "$ckpt" "$run_dir/alignment" "$run_dir/trimal" "$run_dir/modeltest" "$run_dir/trees"

write_checkpoint() {
    stage="$1"; input_file="$2"; output_files="$3"
    python3 - "$stage" "$input_file" "$output_files" <<'PY'
import sys, json, hashlib, time
stage, input_file, output_files = sys.argv[1:4]
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if p else None
json.dump({
    "stage": stage,
    "input_file": input_file,
    "input_sha256": sha(input_file),
    "output_files": output_files.split(","),
    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}, open(f"{stage}.done.json", "w"), indent=2)
PY
}
```

### Stage 1 — align

```bash
FASTA=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['input_fasta'])")
ALIGNER=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['aligner'])")
LARGE=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['large_dataset'])")
SAMPLE=$(basename "$FASTA" .fasta)

if [ "$ALIGNER" = muscle ]; then
    ARG=$([ "$LARGE" = True ] && echo -super5 || echo -align)
    pixi run muscle $ARG "$FASTA" -output "$run_dir/alignment/${SAMPLE}_muscle.fasta"
    MSA="$run_dir/alignment/${SAMPLE}_muscle.fasta"
else
    # --adjustdirection auto-detects and reverse-complements any input sequence
    # that aligns better in the opposite orientation (mixed-strand FASTA is a
    # real risk when combining own sequenced data with NCBI submissions — see
    # phylo-preflight SP7). It prefixes flipped headers with "_R_" — this can
    # break an exact-substring --outgroup match, so re-check SP4 after this stage
    # if the outgroup taxon happened to be one of the flipped sequences.
    pixi run mafft --auto --adjustdirection "$FASTA" > "$run_dir/alignment/${SAMPLE}_mafft.fasta"
    MSA="$run_dir/alignment/${SAMPLE}_mafft.fasta"
fi
cd "$ckpt" && write_checkpoint align "$FASTA" "$MSA"
```

### Stage 2 — trim

```bash
pixi run trimal -in "$MSA" -out "$run_dir/trimal/${SAMPLE}_trimal.fasta" \
    -htmlout "$run_dir/trimal/${SAMPLE}_trimal.html" -nogaps -terminalonly
TRIMMED="$run_dir/trimal/${SAMPLE}_trimal.fasta"
cd "$ckpt" && write_checkpoint trim "$MSA" "$TRIMMED"
```

### Stage 3 — model_select (raxml branch only; skipped for iqtree)

```bash
TREE_TOOL=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['tree_tool'])")
MODEL=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['model'])")

if [ "$TREE_TOOL" = raxml ] && [ -z "$MODEL" ]; then
    pixi run modeltest-ng -i "$TRIMMED" -d nt -p "$(nproc)" -T raxml \
        -o "$run_dir/modeltest/${SAMPLE}_modeltest" --force > "$run_dir/modeltest/log.out" 2>&1
    SITES=$(grep "#sites:" "$run_dir/modeltest/${SAMPLE}_modeltest.out" | awk '{print $2}')
    if [ "$SITES" -lt 500 ]; then
        MODEL=$(awk '/Best model according to AICc/{f=1} f&&/Model:/{print $2; exit}' \
            "$run_dir/modeltest/${SAMPLE}_modeltest.out" | tr -d '[:space:]')
    else
        MODEL=$(awk '/Best model according to BIC/{f=1} f&&/Model:/{print $2; exit}' \
            "$run_dir/modeltest/${SAMPLE}_modeltest.out" | tr -d '[:space:]')
    fi
    # Empty $MODEL here -> SP3.
fi
cd "$ckpt" && write_checkpoint model_select "$TRIMMED" "$run_dir/modeltest/${SAMPLE}_modeltest.out"
```

### Stage 4 — tree

```bash
OUTGROUP=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['outgroup'])")
BS=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['bootstrap_replicates'])")
OUTGROUP_ARG=""; [ -n "$OUTGROUP" ] && OUTGROUP_ARG="--outgroup $OUTGROUP"

if [ "$TREE_TOOL" = raxml ]; then
    pixi run raxml-ng --all --msa "$TRIMMED" --model "$MODEL" --bs-metric fbp,tbe \
        --tree pars{25},rand{25} --bs-trees "$BS" --prefix "$run_dir/trees/$SAMPLE" \
        $OUTGROUP_ARG --force
    # raxml-ng --bs-metric fbp,tbe always produces BOTH support trees — keep both,
    # do not pick one via a glob (that was a bug in v1.0.0's first draft; fixed
    # after the execution battle-test surfaced it). SUPPORT_TREES is now a list.
    SUPPORT_TREES=("$run_dir/trees/${SAMPLE}.raxml.supportFBP" "$run_dir/trees/${SAMPLE}.raxml.supportTBE")
else
    OUTGROUP_ARG=""; [ -n "$OUTGROUP" ] && OUTGROUP_ARG="-o $OUTGROUP"
    pixi run iqtree -s "$TRIMMED" -m MFP -B "$BS" --prefix "$run_dir/trees/$SAMPLE" \
        -T "$(nproc)" $OUTGROUP_ARG
    SUPPORT_TREES=("$run_dir/trees/${SAMPLE}.treefile")
fi
cd "$ckpt" && write_checkpoint tree "$TRIMMED" "$(IFS=,; echo "${SUPPORT_TREES[*]}")"
```

### Stage 5 — render (ASCII tree via gotree)

Render every tree in `SUPPORT_TREES` (one file for iqtree/`.treefile`, two — FBP and TBE — for raxml-ng), not just the first match:

```bash
for t in "${SUPPORT_TREES[@]}"; do
    suffix=$(basename "$t" | sed -E 's/.*\.(supportFBP|supportTBE|treefile)$/\1/')
    pixi run gotree draw text --with-node-labels --with-branch-support --no-branch-lengths \
        -w 120 -i "$t" -o "$run_dir/trees/${SAMPLE}.${suffix}.tree.txt"
done
cd "$ckpt" && write_checkpoint render "${SUPPORT_TREES[0]}" \
    "$(printf '%s.tree.txt,' "$run_dir/trees/${SAMPLE}".{supportFBP,supportTBE,treefile} 2>/dev/null | sed 's/,$//')"
```

For `tree_tool=raxml`, `qc/phylo-qc` reads `${SAMPLE}.supportTBE.tree.txt` as the primary render (TBE is generally the more informative metric for larger trees) and mentions FBP is also available; for `tree_tool=iqtree` there is only `${SAMPLE}.treefile.tree.txt`.

## Interpretation Guidelines

- All 5 checkpoints present and valid → hand off to `qc/phylo-qc`.
- Any stage errors → route to `debug/phylo-debug` with the failing stage name and stderr.
- A stage re-run because an upstream checkpoint was invalidated (SP1/SP2) must delete its own `*.done.json` first, so `qc/phylo-qc` never reads a stale checkpoint alongside fresh output files.

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `muscle: -super5 requires...` / OOM on large inputs | `large_dataset` not set even though N > 500 | Re-run preflight — SP5 auto-sets this from sequence count. |
| `trimal: ... 0 columns` | Alignment nearly all-gap after `-nogaps -terminalonly` | Inspect `*_trimal.html`; sequences may be too divergent to align meaningfully. |
| modeltest-ng empty model string | `.out` parse mismatch (matches MLTree-main's own guarded failure) | SP3 — inspect `modeltest/*.out` directly, or switch to `iqtree`. |
| `raxml-ng: ERROR: model is empty` | `$MODEL` was empty when stage 4 ran | Means stage 3 didn't actually block on SP3 — re-check the model_select checkpoint before re-running stage 4. |
| `raxml-ng ... --outgroup` errors "taxon not found" | Outgroup name doesn't exactly match a FASTA header substring | Should have been caught at preflight SP4; if bypassed, re-run preflight with the corrected name. |
| iqtree `ERROR: Sequences not found for taxon` (outgroup) | Same as above, IQ-TREE's own outgroup check | Same fix. |
| gotree `draw text` produces empty/garbled output | Passed the wrong file, or this checkpoint predates the v1.0.0 fix that renders both FBP and TBE (not just the first glob match) | Re-run stage 5 — `SUPPORT_TREES` now iterates both `*.raxml.supportFBP` and `*.raxml.supportTBE` for the raxml branch, matching MLTree-main's `flatten().filter()` channel pattern that rendered both. |
| Any stage command not found | pixi env missing that tool | `pixi install` in `$RUN_DIR` (or the skill dir), or re-check preflight SP6. |
| `raxml-ng`/`iqtree` outgroup "taxon not found" only on the mafft branch, worked on muscle | mafft's `--adjustdirection` reverse-complemented the outgroup sequence and renamed its header with an `_R_` prefix, so it no longer exact-matches the `outgroup` string from `params.json` | Re-check the aligned FASTA's headers for an `_R_` prefix on the outgroup taxon; update `outgroup` in `params.json` to the prefixed name, or re-run preflight SP4 against the post-align headers. |
| muscle branch has mixed-strand sequences (flagged at preflight SP7) | MUSCLE has no built-in `--adjustdirection`-equivalent auto-orientation flag | Either switch `aligner=mafft` for this run (SP2 governs the swap), or reverse-complement the offending sequences in the input FASTA by hand before running muscle. |

## Verification

- [ ] `checkpoints/align.done.json` through `checkpoints/render.done.json` all exist.
- [ ] Each checkpoint's recorded `input_sha256` matches the current file on disk.
- [ ] `trees/<sample>.tree.txt` (ASCII render) is non-empty.

## What NOT to do

- Do **not** re-run a stage whose checkpoint is valid — that defeats the entire point of checkpointing.
- Do **not** silently proceed past an empty `$MODEL` at stage 4 — route to SP3.
- Do **not** delete a checkpoint without also deleting/regenerating its output files — a checkpoint and its outputs must stay consistent.

## Handoff

> Run complete (or resumed from `<stage>`). All 5 checkpoints written. Next: invoke `qc/phylo-qc` to summarize tree stats (taxa count, mean bootstrap support, alignment length before/after trimming) into `qc-report.md`.

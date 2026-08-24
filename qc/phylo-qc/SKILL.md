---
name: phylo-qc
description: 'Summarize the phylogenetics-agent run into qc-report.md: taxa count, alignment length before/after trimming, mean/min bootstrap support, and the ASCII tree render. Reads the 5 stage checkpoints from build/phylo-builder. Triggers: "summarize the tree", "qc the phylogenetics run", "phylo-qc", "tree report".'
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "summarize the tree"
  - "qc the phylogenetics run"
  - "phylo-qc"
  - "tree report"
---

# phylo-qc

> **v1.0.0.** Final report phase of `phylogenetics-agent`. Reads the run's checkpoints and output files, computes tree-quality metrics, and writes `qc-report.md`.

## 0. Inputs / Outputs contract

### Inputs

| Path | Source | Required? |
| --- | --- | --- |
| `$RUN_DIR/checkpoints/render.done.json` | `build/phylo-builder` | yes |
| `$RUN_DIR/trimal/*_trimal.fasta` | `build/phylo-builder` | yes |
| `$RUN_DIR/trees/*` | `build/phylo-builder` | yes |

### Outputs

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/qc-report.md` | Markdown | Final human-readable report; presence signals `qc-done` stage to the orchestrator |

## 0.5 Ask-User Stop Points

### SP1 — Mean bootstrap support below a usability threshold

| Trigger | Evidence | Action |
| --- | --- | --- |
| Mean FBP/UFBoot support across internal branches < 70 | A tree with weak support across most nodes is not safe to interpret topologically | Ask: "Mean bootstrap support is `<N>`% (< 70%). Pick: (A) accept as a low-confidence tree (common for short/conserved markers), (B) increase `bootstrap_replicates` and re-run stage 4 only, (C) re-check the trimmed alignment length — too little signal may be the real cause" |

**Auto-pick when**: mean support ≥ 70%. No ask — report the number, no stop.

## Procedure

### 1. Gather metrics

```bash
run_dir="$RUN_DIR"
SAMPLE=$(python3 -c "import json,os; print(os.path.splitext(os.path.basename(json.load(open('$run_dir/params.json'))['input_fasta']))[0])")

N_TAXA=$(grep -c '^>' "$run_dir"/trimal/*_trimal.fasta)
ALN_LEN_RAW=$(python3 -c "
import re
seq=''
for line in open('$run_dir/alignment/'+'$SAMPLE'+'_muscle.fasta' if __import__('os').path.exists('$run_dir/alignment/'+'$SAMPLE'+'_muscle.fasta') else '$run_dir/alignment/'+'$SAMPLE'+'_mafft.fasta'):
    if line.startswith('>'): break
print(0)
"
ALN_LEN_TRIMMED=$(awk '/^>/{if(s)print length(s);s=""} !/^>/{s=s$0} END{if(s)print length(s)}' \
    "$run_dir"/trimal/*_trimal.fasta | head -1)

# Bootstrap support: parse from .raxml.support* or .treefile (Newick internal-node labels)
python3 - <<'PY'
import re, glob, statistics
files = glob.glob("$run_dir/trees/*.raxml.support*") or glob.glob("$run_dir/trees/*.treefile")
supports = []
for f in files:
    txt = open(f).read()
    # crude Newick support extraction: numbers immediately after a closing paren
    supports += [float(x) for x in re.findall(r"\)([0-9]+(?:\.[0-9]+)?):", txt)]
if supports:
    print(f"Mean support: {statistics.mean(supports):.1f}")
    print(f"Min support:  {min(supports):.1f}")
    print(f"N internal nodes: {len(supports)}")
else:
    print("No support values parsed — check tree file format.")
PY
```

### 2. Write `qc-report.md`

```markdown
# phylogenetics-agent QC report

Run:        $RUN_DIR
Generated:  <ISO8601>
Pipeline:   phylogenetics-agent v1.0.0

## Overall verdict

**GO** ✅ *(or GO-WITH-WARNINGS ⚠️ if mean support < 70%)*

## Run configuration

| Param | Value |
|---|---|
| Aligner | muscle / mafft |
| Tree tool | raxml / iqtree |
| Model | <model or "ModelFinder (iqtree)"> |
| Bootstrap replicates | <N> |
| Outgroup | <taxon or "none — unrooted"> |

## Metrics

| Metric | Value |
|---|---|
| Taxa | <N> |
| Trimmed alignment length | <N> bp/aa |
| Mean bootstrap support (internal nodes) | <N>% |
| Min bootstrap support | <N>% |

## Tree (ASCII render)

\`\`\`
<contents of trees/<sample>.tree.txt>
\`\`\`

## Files

- Alignment: `alignment/<sample>_<aligner>.fasta`
- Trimmed alignment: `trimal/<sample>_trimal.fasta` (+ `.html` report)
- Tree: `trees/<sample>.raxml.bestTree` or `trees/<sample>.treefile`
- Support tree(s): `trees/<sample>.raxml.support{FBP,TBE}` or embedded in `.treefile`

## Reproducibility

- params.json: $RUN_DIR/params.json
- checkpoints: $RUN_DIR/checkpoints/*.done.json
- this report: $RUN_DIR/qc-report.md (regenerable via this skill)
```

## Interpretation Guidelines

- **GO**: mean bootstrap support ≥ 70%, no missing output files.
- **GO-WITH-WARNINGS**: mean support < 70% (SP1) or outgroup was dropped at preflight — tree is usable but topology confidence should be caveated.
- **NO-GO**: a required output file (tree, trimmed alignment) is missing — the run did not actually complete despite checkpoints existing (route to `debug/phylo-debug`).

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `No support values parsed` | Newick format uses a different support-label convention (e.g. support as internal node *names* not decimals) | Open the tree file directly and adjust the regex, or read `*.iqtree`'s "NOTE" section which states the exact convention used. |
| `trimal/*_trimal.fasta` missing despite `render.done.json` present | Checkpoint exists but output was deleted after the fact | Re-run `build/phylo-builder` for the `trim` stage — the checkpoint's `input_sha256` should still validate against the alignment file. |
| Mean support is suspiciously exactly 100 for every node | Only 1 bootstrap replicate was effectively run, or `.treefile` support values weren't ultrafast-bootstrap (parsing picked up branch lengths instead of support) | Check `params.json: bootstrap_replicates` and re-inspect the regex against a sample of the actual file. |

## Verification

- [ ] `$RUN_DIR/qc-report.md` exists.
- [ ] Metrics table is populated (no `<N>` placeholders left).
- [ ] ASCII tree render is embedded and non-empty.

## Handoff

> QC complete. Verdict: `<verdict>`. `qc-report.md` is the final deliverable — the orchestrator's `qc-done` stage just shows it to the user. Optional next steps (not gated, invoke only if the user asks): `visualize/phylo-itol` for interactive iTOL label styling / colorstrip datasets, or `visualize/phylo-render` for an offline SVG/PDF/PNG figure.

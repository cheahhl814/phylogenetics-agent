---
name: phylo-preflight
description: 'Validate a multi-FASTA input for the phylogenetics-agent skill before any alignment/tree work starts. Checks sequence count, duplicate/empty headers, sequence type (nt vs aa) consistency, outgroup taxa presence, and tool availability. Writes preflight.md + params.json. Triggers: "preflight phylogenetics", "validate FASTA for tree", "phylo-preflight".'
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "preflight phylogenetics"
  - "validate FASTA for tree"
  - "phylo-preflight"
  - "check sequences before tree building"
---

# phylo-preflight

> **v1.0.0.** Input-validation phase of `phylogenetics-agent`. Mirrors `bettamt-preflight`: gather inputs → compute evidence → write `params.json` (machine contract) + `preflight.md` (human audit). Never invokes `build/phylo-builder` directly.

## When to Use This Skill

Use when the user provides a multi-FASTA file and wants a phylogenetic tree built from it, before any alignment work starts.

Do NOT use if `params.json` for this run already exists with a `GO`/`GO-WITH-WARNINGS` verdict — re-running preflight without deleting it first re-triggers stage detection confusion in the orchestrator.

## 0. Inputs / Outputs contract

### Inputs (consumed)

| Path                                      | Source | Required? |
| ----------------------------------------- | ------ | --------- |
| User-provided multi-FASTA path            | User   | yes       |
| `$RUN_DIR` (default: cwd)                 | User   | yes       |
| `outgroup` taxon name(s), comma-separated | User   | optional  |

### Outputs (produced)

| Path                              | Owner      | Format   | Notes                                      |
| --------------------------------- | ---------- | -------- | ------------------------------------------ |
| `$RUN_DIR/params.json`            | this skill | JSON     | Machine contract for `build/phylo-builder` |
| `$RUN_DIR/preflight.md`           | this skill | Markdown | Human audit trail                          |
| `$RUN_DIR/preflight_evidence.txt` | this skill | text     | Raw evidence                               |

### Verdict gate

`build/phylo-builder` refuses to run unless `preflight.md` verdict is `GO` or `GO-WITH-WARNINGS`.

## 0.5 Ask-User Stop Points

### SP1 — Fewer than 4 sequences

| Trigger                    | Evidence                                                                                         | Action                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `grep -c '^>' <fasta>` < 4 | A tree needs ≥ 4 taxa to be meaningful (3 taxa = unrooted star, no internal branches to support) | Ask: "Only `<N>` sequences found. Pick: (A) add more sequences, (B) proceed anyway (tree will be trivial/unsupported), (C) abort" |

**Auto-pick when**: ≥ 4 sequences. No ask.

### SP2 — Duplicate or empty FASTA headers

| Trigger                                                                         | Evidence                                                                   | Action                                                                                                                                                         |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `grep '^>' <fasta> \| sort \| uniq -d` is non-empty, or any header is `>` alone | Muscle/RAxML/IQ-TREE will silently collide or crash on duplicate/empty IDs | Ask: "Found `<N>` duplicate or empty headers: `<list>`. Pick: (A) I'll dedupe/rename now, (B) auto-suffix duplicates (`_1`, `_2`, ...) and proceed, (C) abort" |

**Auto-pick when**: no duplicates/empty headers. No ask.

### SP3 — Mixed sequence type (nucleotide + amino acid)

| Trigger                                                                 | Evidence                                                   | Action                                                                                                                                                                      |
| ----------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Some sequences match `^[ACGTUN-]+$` (case-insensitive) and others don't | Aligners and RAxML-NG/IQ-TREE need one consistent alphabet | Ask: "Sequences look mixed nt/aa. Pick: (A) treat all as nucleotide (drop non-nt chars as ambiguity codes), (B) treat all as amino acid, (C) I'll fix the input, (D) abort" |

**Auto-pick when**: ≥ 95% of sequences unambiguously match one alphabet. Default: nucleotide (MLTree's original scope).

### SP4 — Outgroup taxon not found in FASTA headers

| Trigger                                                                               | Evidence                                                                                     | Action                                                                                                                                                                   |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| User supplied `--outgroup <name>` but `<name>` is not a substring of any FASTA header | RAxML-NG/IQ-TREE will error at the tree stage, hours into a bootstrap run, if not caught now | Ask: "Outgroup `<name>` not found in any header. Pick: (A) I'll give the correct taxon name, (B) drop the outgroup (tree will be unrooted / midpoint-rooted), (C) abort" |

**Auto-pick when**: every named outgroup taxon matches a header. No ask.

### SP5 — Large dataset threshold

| Trigger                                                                        | Evidence                                                                                    | Action                                                                                                                                            |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sequence count > 500 AND aligner is `muscle` AND user didn't specify `-super5` | MUSCLE's default `-align` algorithm is impractical above ~500 seqs (MLTree's own threshold) | Auto-pick `large_dataset: true` (uses `-super5`) and note it in `preflight.md` — no ask needed, this mirrors MLTree's documented default exactly. |

**Auto-pick when**: always (this is a deterministic threshold, not a judgment call).

### SP6 — Tool availability

| Trigger                                                                                                                                                                   | Evidence     | Action                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `pixi run --manifest-path pixi.toml <tool> --version` fails for any of muscle/mafft/trimal/modeltest-ng/raxml-ng/iqtree/gotree needed by the chosen `aligner`/`tree_tool` | Missing tool | Ask: "`<tool>` is not available. Pick: (A) `pixi install` now, (B) pick a different aligner/tree_tool that avoids `<tool>`, (C) abort" |

**Auto-pick when**: all needed tools resolve. Note: only the tools needed for the *chosen* `aligner`/`tree_tool` are required — e.g. if `tree_tool=iqtree`, `modeltest-ng` is not needed (IQ-TREE's ModelFinder replaces it).

## Procedure

### 1. Gather inputs

| Input                  | Required? | Default                       |
| ---------------------- | --------- | ----------------------------- |
| FASTA path             | yes       | —                             |
| `aligner`              | no        | `muscle`                      |
| `tree_tool`            | no        | `raxml`                       |
| `model` (raxml only)   | no        | empty → modeltest-ng picks it |
| `outgroup`             | no        | empty (unrooted/midpoint)     |
| `bootstrap_replicates` | no        | `1000`                        |

### 2. Compute evidence

```bash
FASTA="$1"
N_SEQ=$(grep -c '^>' "$FASTA")
echo "Sequence count: $N_SEQ" | tee -a "$RUN_DIR/preflight_evidence.txt"

DUP_HEADERS=$(grep '^>' "$FASTA" | sort | uniq -d)
echo "Duplicate headers: ${DUP_HEADERS:-none}" | tee -a "$RUN_DIR/preflight_evidence.txt"

EMPTY_HEADERS=$(grep -c '^>[[:space:]]*$' "$FASTA")
echo "Empty headers: $EMPTY_HEADERS" | tee -a "$RUN_DIR/preflight_evidence.txt"

# Rough nt-vs-aa check: sample non-header lines, count chars outside ACGTUN-
NON_NT_FRACTION=$(grep -v '^>' "$FASTA" | tr -d '\n' | tr -d 'ACGTUNacgtun-' | wc -c)
TOTAL_CHARS=$(grep -v '^>' "$FASTA" | tr -d '\n' | wc -c)
echo "Non-nucleotide character fraction: $NON_NT_FRACTION / $TOTAL_CHARS" | tee -a "$RUN_DIR/preflight_evidence.txt"

LARGE_DATASET=$([ "$N_SEQ" -gt 500 ] && echo true || echo false)
echo "Large dataset (> 500 seqs): $LARGE_DATASET" | tee -a "$RUN_DIR/preflight_evidence.txt"

if [ -n "$OUTGROUP" ]; then
    for TAXON in $(echo "$OUTGROUP" | tr ',' ' '); do
        grep -q "$TAXON" <(grep '^>' "$FASTA") \
            && echo "Outgroup taxon '$TAXON': found" | tee -a "$RUN_DIR/preflight_evidence.txt" \
            || echo "Outgroup taxon '$TAXON': NOT FOUND" | tee -a "$RUN_DIR/preflight_evidence.txt"
    done
fi

for TOOL in "$ALIGNER" trimal $([ "$TREE_TOOL" = raxml ] && [ -z "$MODEL" ] && echo modeltest-ng) "$([ $TREE_TOOL = raxml ] && echo raxml-ng || echo iqtree)" gotree; do
    pixi run --manifest-path "$RUN_DIR/pixi.toml" "$TOOL" --version >/dev/null 2>&1 \
        && echo "Tool $TOOL: available" | tee -a "$RUN_DIR/preflight_evidence.txt" \
        || echo "Tool $TOOL: NOT available" | tee -a "$RUN_DIR/preflight_evidence.txt"
done
```

### 3. Write outputs

`params.json` (consumed by `build/phylo-builder`):

```json
{
  "input_fasta": "/abs/path/sequences.fasta",
  "n_sequences": 42,
  "aligner": "muscle",
  "large_dataset": false,
  "tree_tool": "raxml",
  "model": "",
  "outgroup": "",
  "bootstrap_replicates": 1000,
  "sequence_type": "nucleotide",
  "verdict": "GO",
  "warnings": [],
  "generated": "<ISO8601>"
}
```

`preflight.md` follows the standard table format: Evidence table (sequence count, duplicate/empty headers, nt/aa check, large-dataset flag, outgroup match, tool availability) → Recommendations → Handoff to `build/phylo-builder`.

## Interpretation Guidelines

- **GO**: ≥ 4 sequences, no duplicate/empty headers, alphabet unambiguous, outgroup (if given) matches, all needed tools available.
- **GO-WITH-WARNINGS**: auto-fixed duplicates, or outgroup dropped, or large-dataset auto-flag set — proceed but the warning is visible in the run report.
- **NO-GO**: < 4 sequences and user declines to proceed, or a needed tool is missing and the user has no path to install it.

## Troubleshooting — Signature library

| Signature                                  | Likely cause                                                                           | Fix                                                                                                                                        |
| ------------------------------------------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `grep: <fasta>: No such file or directory` | Wrong path                                                                             | Verify with `ls -la`.                                                                                                                      |
| `Sequence count: 0`                        | File isn't FASTA (no `>` headers) or is empty                                          | Check the file with `head`.                                                                                                                |
| Duplicate headers found                    | Two sequences share an ID (common when concatenating exports from different databases) | Dedupe or auto-suffix (SP2).                                                                                                               |
| Non-nucleotide fraction > 5% but < 95%     | Ambiguity codes (IUPAC) or genuinely mixed input                                       | Check with `head -20 <fasta>`; IUPAC codes (R,Y,S,W,K,M...) are fine for nt, just extend the regex — don't treat as mixed unless truly aa. |
| Outgroup not found                         | Typo, or header uses a different delimiter/format than expected                        | `grep '^>' <fasta> \| grep -i '<partial-name>'` to find the real header string.                                                            |
| `pixi run <tool> --version` hangs          | Tool not installed and pixi trying to solve on the fly                                 | `pixi install` first, then re-check.                                                                                                       |

## Verification

- [ ] `$RUN_DIR/params.json` exists and is valid JSON.
- [ ] `$RUN_DIR/preflight.md` exists with overall verdict.
- [ ] Verdict is `GO` or `GO-WITH-WARNINGS` before handing off.

## Handoff

> Preflight complete. Verdict: `<verdict>`. Next: invoke `build/phylo-builder` — it will execute `align → trim → model_select → tree → render`, checkpointing after each stage.

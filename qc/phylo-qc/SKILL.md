---
name: phylo-qc
description: 'Summarize the phylogenetics-agent run into qc-report.md: taxa count, alignment length before/after trimming, mean/min bootstrap support, weak-clade list, long-branch outlier detection, outgroup monophyly check, and the ASCII tree render. Reads the 5 stage checkpoints from build/phylo-builder. Triggers: "summarize the tree", "qc the phylogenetics run", "phylo-qc", "tree report".'
version: 1.2.0
updated: "2026-09-08"
triggers:
  - "summarize the tree"
  - "qc the phylogenetics run"
  - "phylo-qc"
  - "tree report"
---

# phylo-qc

> **v1.1.0.** Final report phase of `phylogenetics-agent`. Reads the run's checkpoints and output files, computes tree-quality metrics, runs automated result interpretation (weak clades, long-branch outliers, outgroup monophyly -- all via `gotree stats`, verified live, no hand-rolled Newick parsing), and writes `qc-report.md`.

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

### SP2 — Long-branch outlier tip(s) detected

| Trigger | Evidence | Action |
| --- | --- | --- |
| `qc_report.py` flags a terminal branch length as a MAD outlier (verified live: `gotree stats edges` gives per-tip branch length directly, no parsing needed) | An unusually long branch is a classic signature of a misidentified/contaminant sequence, or an alignment artifact around that tip | Ask: "Tip(s) `<names>` have unusually long branches. Pick: (A) keep as-is (may be genuinely divergent), (B) inspect that sequence's identity/quality, (C) drop it via `prune/phylo-prune --exclude-file`" |

**Auto-pick when**: zero long-branch outliers. No ask.

### SP3 — Outgroup not monophyletic

| Trigger | Evidence | Action |
| --- | --- | --- |
| `params.json` names an outgroup and `gotree stats monophyletic` returns `false` for its matched tip(s) | The outgroup is nested inside the ingroup in the resulting tree — either the outgroup choice was wrong, the alignment/model is misleading the tree, or this is a genuine (surprising) biological result | Ask: "The outgroup doesn't form a monophyletic group outside the ingroup. Pick: (A) accept as a real result (needs a biological explanation), (B) re-check the outgroup taxon choice and re-run preflight, (C) treat as a QC concern and route to `debug/phylo-debug`" |

**Auto-pick when**: no outgroup was set, or it is monophyletic. No ask.

## Procedure

### 1. Locate inputs

```bash
run_dir="$RUN_DIR"
SAMPLE=$(python3 -c "import json,os; print(os.path.splitext(os.path.basename(json.load(open('$run_dir/params.json'))['input_fasta']))[0])")
TOOL=$(python3 -c "import json; print(json.load(open('$run_dir/params.json'))['tree_tool'])")

if [ "$TOOL" = iqtree ]; then
    TREE="$run_dir/trees/${SAMPLE}.treefile"
    ASCII="$run_dir/trees/${SAMPLE}.treefile.tree.txt"
else
    TREE="$run_dir/trees/${SAMPLE}.raxml.supportTBE"
    ASCII="$run_dir/trees/${SAMPLE}.supportTBE.tree.txt"
fi
```

### 2. Compute metrics + automated interpretation, write `qc-report.md`

```bash
cd /path/to/phylogenetics-agent   # skill root, so `pixi run gotree` resolves

python3 qc/phylo-qc/scripts/qc_report.py "$TREE" \
    --trimmed-aln "$run_dir/trimal/${SAMPLE}_trimal.fasta" \
    --raw-aln "$run_dir/alignment/${SAMPLE}_muscle.fasta" \
    --params "$run_dir/params.json" \
    --ascii-tree "$ASCII" \
    -o "$run_dir/qc-report.md" \
    --gotree-cmd "pixi run gotree"
```

`qc_report.py` (verified live against a real `.contree`/`.treefile` output, both a single-tip and a multi-tip outgroup case):

- Parses `gotree stats edges` for per-branch length/support/topodepth — no regex over Newick text.
- **Support-scale normalization (v1.2.0)**: fraction-encoded trees (RAxML-NG `.raxml.supportTBE`/`.supportFBP`, 0–1 fractions) are rescaled ×100 before thresholding/formatting; percent-encoded trees (IQ-TREE `.contree` etc.) pass through unchanged. Scale is auto-detected (max internal support ≤ 1 ⇒ fractions). Before this fix, TBE supports printed unscaled (mean "0.5%" instead of 50.9%) and every clade was falsely flagged below the 70 threshold.
- **Weak clades**: internal edges below `--support-threshold` (default 70), reported with clade size.
- **Long-branch outliers**: terminal edges whose length exceeds `median + 3×MAD` (default `--mad-k 3.0`) — skipped automatically if <4 tips (MAD is meaningless that small).
- **Outgroup monophyly**: if `params.json`'s `outgroup` field is non-empty, matches it against real tip names (substring match, same convention as preflight) and runs `gotree stats monophyletic`.
- Writes `GO` if no flags raised, `GO-WITH-WARNINGS` if any of the above fired.

### 3. Report to the user

Read `$run_dir/qc-report.md`'s "Automated interpretation" section and route through SP1/SP2/SP3 for any flags raised.

## Interpretation Guidelines

- **GO**: mean bootstrap support ≥ 70%, no weak clades / long-branch outliers / outgroup non-monophyly flagged, no missing output files.
- **GO-WITH-WARNINGS**: any automated-interpretation flag fired (SP1/SP2/SP3) or outgroup was dropped at preflight — tree is usable but the specific caveat should be surfaced to the user, not just the aggregate mean-support number.
- **NO-GO**: a required output file (tree, trimmed alignment) is missing — the run did not actually complete despite checkpoints existing (route to `debug/phylo-debug`).

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `ERROR: gotree stats edges failed` | Input tree path wrong, or `build/phylo-builder` hasn't produced it yet (`.treefile` for iqtree vs `.raxml.supportTBE` for raxml) | Check `checkpoints/tree.done.json`'s `output_files` for the real path. |
| `trimal/*_trimal.fasta` missing despite `render.done.json` present | Checkpoint exists but output was deleted after the fact | Re-run `build/phylo-builder` for the `trim` stage — the checkpoint's `input_sha256` should still validate against the alignment file. |
| Mean support is suspiciously exactly 100 for every node | Only 1 bootstrap replicate was effectively run | Check `params.json: bootstrap_replicates`. |
| Long-branch outlier list is empty even though a tip "looks" long on the ASCII render | Fewer than 4 tips in the tree — `qc_report.py` skips MAD-based outlier detection below that size since the statistic is meaningless that small | Not a bug; inspect the ASCII render / `gotree stats edges` output manually for very small trees. |
| Outgroup monophyly section missing from the report | `params.json`'s `outgroup` field is empty, or the substring match against tip names found zero tips (e.g. an `_R_`-flipped tip name — see `preflight/phylo-preflight` SP7) | Check `gotree stats tips -i <tree>` for the actual tip names if you expected a match. |

## Verification

- [ ] `$RUN_DIR/qc-report.md` exists.
- [ ] Metrics table is populated (no `<N>` placeholders left).
- [ ] "Automated interpretation" section present; any flags routed through SP1/SP2/SP3.
- [ ] ASCII tree render is embedded and non-empty.

## Handoff

> QC complete. Verdict: `<verdict>`. `qc-report.md` is the final deliverable — the orchestrator's `qc-done` stage just shows it to the user. If long-branch outliers were flagged, mention `prune/phylo-prune` as the way to drop them. Optional next steps (not gated, invoke only if the user asks): `visualize/phylo-itol` for interactive iTOL label styling / colorstrip datasets, or `visualize/phylo-render` for an offline SVG/PDF/PNG figure.

---
name: phylo-prune
description: 'Prune the final tree from build/phylo-builder down to a curated subset of taxa -- keep list, exclude list, or diff against a reference pruned tree -- via gotree prune, preserving branch lengths and support values. Triggers: "prune the tree", "remove these taxa", "drop misidentified sequences", "phylo-prune".'
version: 1.0.0
updated: "2026-08-25"
triggers:
  - "prune the tree"
  - "remove these taxa"
  - "drop misidentified sequences"
  - "exclude these sequences from the tree"
  - "phylo-prune"
disable-model-invocation: true
---

# phylo-prune

> **v1.0.0.** Optional stage of `phylogenetics-agent`, run after `qc/phylo-qc` (before or alongside `visualize/phylo-itol` / `visualize/phylo-render`, both of which can consume the pruned tree instead of the full one). Wraps `gotree prune` -- no hand-rolled Newick parsing needed, since gotree already parses IQ-TREE's `.treefile`/`.contree` support-before-colon convention correctly and, verified live, sums branch lengths correctly when collapsing single-child internal nodes left behind by a prune.

## When to Use This Skill

Use after `qc/phylo-qc` has produced `qc-report.md`, when the user wants to:
- Drop misidentified or low-quality sequences before publishing.
- Exclude specific taxa (e.g. mitochondrial-genome entries they don't want to show).
- Cut the tree down to a curated subset, matching an existing reference pruned tree from a related analysis.

Do NOT use this to change which sequences go *into* the alignment/tree build -- that's a `build/phylo-builder` re-run with a filtered input FASTA. This skill only trims tips from an already-built tree.

## 0. Inputs / Outputs contract

### Inputs

| Path | Source | Required? |
| --- | --- | --- |
| `$RUN_DIR/checkpoints/tree.done.json` | `build/phylo-builder` | yes |
| the tree file itself (`.treefile` for iqtree, `.raxml.supportTBE`/`.supportFBP` for raxml-ng) | `build/phylo-builder` | yes |
| Exactly one of: `--keep NAME...`, `--keep-file FILE`, `--exclude-file FILE`, `--reference-tree FILE` | User | yes |

### Outputs

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/pruned/<sample>_pruned.nwk` | Newick | branch lengths + support values preserved |
| `$RUN_DIR/pruned/<sample>_pruned.nwk.report.txt` | Text | tip counts before/after, removed names, any requested names not found |

## 0.5 Ask-User Stop Points

### SP1 -- Determine the keep/exclude mode

| Trigger | Evidence | Action |
| --- | --- | --- |
| User said "prune the tree" without specifying how | No default mode makes sense -- keep vs. exclude are opposite operations | Ask: "How should I select taxa? (A) give me a list of names to **keep**, (B) give me a list of names to **exclude** (e.g. misidentified sequences, mitogenomes), (C) I have a reference pruned tree from a related analysis -- match its tip set" |

**Auto-pick when**: the user's request already names the taxa and the verb ("keep only X, Y, Z" vs "remove X, Y, Z") -- infer `--keep`/`--exclude-file` directly, no need to ask.

### SP2 -- Requested name not found in the tree

| Trigger | Evidence | Action |
| --- | --- | --- |
| `prune_tree.py` exits with `N requested name(s) not found` (verified live: gotree itself silently ignores unknown names rather than erroring, so this check runs in the wrapper before calling gotree) | The name doesn't match any tip in `gotree stats tips` | **Recommend**: if `build/phylo-builder` ran with mafft `--adjustdirection` (see `preflight/phylo-preflight` SP7), a flipped tip's tree name carries an `_R_` prefix -- check `gotree stats tips -i <tree>` for the real name first. Ask: "(A) fix the name and re-run, (B) proceed anyway with `--force` (missing names are simply ignored, not an error)" |

**Auto-pick when**: zero missing names. No ask.

### SP3 -- Result would leave too few tips

| Trigger | Evidence | Action |
| --- | --- | --- |
| gotree stderr contains `only made of two tips` / `only made of one tip` (verified live: gotree hard-refuses to prune below 3 tips) | The keep/exclude set is too aggressive for a meaningful tree | Ask: "Pruning to this set leaves fewer than 3 tips, which gotree refuses to produce. Which taxa should stay in, at minimum?" |

**Auto-pick when**: n/a -- this always requires user input, there's no sensible default subset to fall back to.

### SP4 -- Overwrite existing pruned output

| Trigger | Evidence | Action |
| --- | --- | --- |
| `$RUN_DIR/pruned/<sample>_pruned.nwk` already exists | A previous prune run is present | Ask before overwriting: "(A) overwrite, (B) write to a new name (e.g. `_pruned_v2.nwk`)" |

**Auto-pick when**: no existing file at that path.

## Procedure

### 1. Locate the tree file

```bash
run_dir="$RUN_DIR"
tool=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['tree_tool'])")
sample=$(python3 -c "import json,os;print(os.path.splitext(os.path.basename(json.load(open('$run_dir/params.json'))['input_fasta']))[0])")

if [ "$tool" = iqtree ]; then
    TREE="$run_dir/trees/${sample}.treefile"
else
    TREE="$run_dir/trees/${sample}.raxml.supportTBE"
fi
mkdir -p "$run_dir/pruned"
```

### 2. Run the prune

```bash
cd /path/to/phylogenetics-agent   # skill root, so `pixi run gotree` resolves

# Keep mode
python3 prune/phylo-prune/scripts/prune_tree.py "$TREE" \
    --keep Taxon_a Taxon_b Taxon_c \
    -o "$run_dir/pruned/${sample}_pruned.nwk" \
    --gotree-cmd "pixi run gotree"

# Exclude mode (misidentified sequences, mitogenomes, etc.)
python3 prune/phylo-prune/scripts/prune_tree.py "$TREE" \
    --exclude-file /path/to/exclude_list.txt \
    -o "$run_dir/pruned/${sample}_pruned.nwk" \
    --gotree-cmd "pixi run gotree"

# Match a reference pruned tree from a related analysis
python3 prune/phylo-prune/scripts/prune_tree.py "$TREE" \
    --reference-tree /path/to/reference_pruned.nwk \
    -o "$run_dir/pruned/${sample}_pruned.nwk" \
    --gotree-cmd "pixi run gotree"
```

### 3. Report to the user

Read `$run_dir/pruned/${sample}_pruned.nwk.report.txt` and surface the tip count before/after and the removed-names list.

## Interpretation Guidelines

- **Tip count drops exactly to the expected size, 0 missing names**: clean prune, no follow-up needed.
- **Some requested names missing**: route through SP2 before proceeding -- likely a typo or an `_R_`-flip mismatch, not intentional.
- **gotree refuses (<3 tips)**: route through SP3 -- the request itself needs revising, not a bug.

## Troubleshooting -- Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `N requested name(s) not found in <tree>` | Typo, or the tip was reverse-complemented by mafft `--adjustdirection` upstream and now carries an `_R_` prefix (see `preflight/phylo-preflight` SP7 and `build/phylo-builder` Stage 1) | Run `gotree stats tips -i <tree>` first and match the exact name; re-run with the corrected name, or `--force` to ignore. |
| `the requested keep/exclude set leaves too few tips` | gotree refuses trees with < 3 tips (verified live) | Keep at least 3 taxa; a 2-taxon "tree" is a degenerate single edge, not meaningful phylogenetically. |
| `gotree: command not found` | Script invoked without `--gotree-cmd "pixi run gotree"` outside an activated pixi shell | Always pass `--gotree-cmd`, or run inside `pixi shell`. |
| Pruned tree's branch lengths look longer than expected on a formerly-single-child node | Expected, not a bug -- gotree sums the collapsed node's branch length into the remaining edge (verified live: standard phylogenetic practice, preserves total root-to-tip distance) | No fix needed; this is correct. |
| `ERROR: gotree stats tips failed` | Input tree path wrong, or `build/phylo-builder` hasn't produced it yet | Check `checkpoints/tree.done.json`'s `output_files` for the real path. |

## Verification

- [ ] `$RUN_DIR/pruned/<sample>_pruned.nwk` exists and parses (`gotree stats tips -i <file>` succeeds).
- [ ] Report's "tips after" count matches what the user asked for.
- [ ] No unexpected names in "removed" list.

## What NOT to do

- Do **not** hand-roll a Newick parser for this -- `gotree` already handles the IQ-TREE support-before-colon convention and branch-length collapse math correctly (verified live against this pipeline's own `.treefile` and `.contree` outputs).
- Do **not** silently proceed past SP2 without asking -- a missing name is very often the `_R_`-prefix strand-flip gotcha, not a real absence, and guessing wrong here silently changes which taxa end up in a published figure.

## Handoff

> Prune complete. `pruned/<sample>_pruned.nwk` written (`<N>` -> `<M>` tips). To visualize the pruned tree instead of the full one, point `visualize/phylo-itol` or `visualize/phylo-render` at this file instead of the one in `trees/`.

---
name: phylo-itol
description: 'Generate iTOL (itol.embl.de) annotation datasets from the final tree produced by build/phylo-builder: italic tip-label styling (always) and a colorstrip grouping taxa by genus/clade/any user-defined grouping (when a group source is given). If params.json names an outgroup, the tree is rerooted on it via `gotree reroot outgroup` before upload. Tip names come from gotree stats tips, not regex Newick parsing. Triggers: "visualize the tree", "iTOL annotation", "colorstrip", "style the tree labels", "phylo-itol".'
version: 1.1.0
updated: "2026-08-25"
triggers:
  - "visualize the tree"
  - "iTOL annotation"
  - "colorstrip"
  - "style the tree labels"
  - "phylo-itol"
  - "annotate the phylogenetic tree"
---

# phylo-itol

> **v1.1.0.** Optional visualization/interpretation phase of `phylogenetics-agent`, run after `qc/phylo-qc`. Generates iTOL (https://itol.embl.de) dataset files the user uploads alongside their Newick tree for interactive, publication-quality rendering — this skill does not render an image itself, iTOL does. If `params.json` names an outgroup, the tree is rerooted on it first via `gotree reroot outgroup` (verified live, including the non-monophyletic-outgroup warning path) — iTOL's default rendering otherwise leaves the tree exactly as `build/phylo-builder` produced it (unrooted / arbitrarily rooted), which misrepresents the intended ingroup/outgroup relationship. Inspired by two project-local scripts (`generate_itol_styles.py`, `generate_itol_colorstrip.py`) but generalized: tip names come from `gotree stats tips` (robust) instead of a hand-rolled Newick regex, and the group→color mapping is user-supplied (TSV or regex) instead of a hardcoded taxonomy table.

## When to Use This Skill

Use after `qc/phylo-qc` has produced `qc-report.md`, when the user wants:
- Italicized tip labels for a publication-style tree (always available, no extra input needed).
- A colored strip grouping taxa by genus, clade, sample source, or any other tip-name-derived or user-supplied category.

Do NOT use if the user just wants the plain-text ASCII tree from `qc/phylo-qc` — that's already sufficient for a quick look.

## 0. Inputs / Outputs contract

### Inputs

| Path | Source | Required? |
| --- | --- | --- |
| `$RUN_DIR/checkpoints/tree.done.json` | `build/phylo-builder` | yes |
| the tree file itself (`.treefile` for iqtree, or `.raxml.supportFBP`/`.supportTBE` for raxml) | `build/phylo-builder` | yes |
| A group source: `--groups-tsv <tip\tgroup file>` OR `--regex <pattern>` | User | only for the colorstrip; labels-only doesn't need one |

### Outputs

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/itol/<sample>_rooted.nwk` | Newick | Only if `params.json` has a non-empty `outgroup` that matched a tip — this is the file to upload, **not** the original `trees/*` file |
| `$RUN_DIR/itol/<sample>_labels.txt` | iTOL `TREE_COLORS` dataset | Always generated — italicizes every tip label |
| `$RUN_DIR/itol/<sample>_colorstrip.txt` | iTOL `DATASET_COLORSTRIP` dataset | Only if a group source was given |
| `$RUN_DIR/itol/<sample>_legend.md` | Markdown | group → color → tip-count table |

Upload the tree file (`<sample>_rooted.nwk` if it exists, otherwise the original `trees/*` file) and these `.txt` datasets together at https://itol.embl.de/upload.cgi (drag the tree first, then drag each dataset file onto the rendered tree).

## 0.5 Ask-User Stop Points

### SP1 — No group source given for the colorstrip

| Trigger | Evidence | Action |
| --- | --- | --- |
| User asked for a colorstrip/grouped visualization but gave neither `--groups-tsv` nor `--regex` | Colorstrip needs a group source, there's no sensible default | Ask: "How should tips be grouped for the colorstrip? Pick: (A) I'll give a regex (e.g. `^([A-Za-z]+)_` to group by genus, matching the tip-naming convention this skill's own preflight produces), (B) I'll supply a `tip_name<TAB>group` TSV file, (C) skip the colorstrip — labels-only" |

**Auto-pick when**: user only asked for label styling (no grouping mentioned). Default: labels-only, skip colorstrip.

### SP2 — Regex leaves tips unmatched

| Trigger | Evidence | Action |
| --- | --- | --- |
| `itol_colorstrip.py`'s stderr reports `N/M tips have no group` | Some tip names don't match the given pattern | Ask: "`<N>` of `<M>` tips didn't match the regex and were grouped as `unclassified` (grey). Pick: (A) accept as-is, (B) give a corrected regex and re-run, (C) switch to a `--groups-tsv` file for full control" |

**Auto-pick when**: 0 unmatched tips. No ask.

### SP3 — Color override conflict

| Trigger | Evidence | Action |
| --- | --- | --- |
| `--colors-tsv` assigns a color to a group name that doesn't appear in the actual tip groups | Likely a typo in the group name | Ask: "`--colors-tsv` names group `<X>` but no tip was assigned to it. Pick: (A) fix the group name, (B) ignore (color unused, no harm), (C) abort" |

**Auto-pick when**: every override group name is actually used. No ask.

### SP4 — Outgroup is not monophyletic (reroot still applied)

| Trigger | Evidence | Action |
| --- | --- | --- |
| `gotree reroot outgroup` prints `Warning! The given outgroup is not Monophyloetic, and may result in inappropriate rerooting` (verified live) | The named outgroup taxa don't form a clean clade — gotree still reroots at the LCA of the given tips rather than failing, so the result may not be the rooting the user expects | Ask: "The outgroup isn't monophyletic in this tree — gotree rerooted at the common ancestor of the given tips anyway, which may not be what you want. Pick: (A) accept this rooting, (B) re-check the outgroup choice (see `qc/phylo-qc` SP3 — this is the same underlying issue), (C) leave the tree unrooted for now" |

**Auto-pick when**: no warning printed, or no outgroup was set. No ask.

## Procedure

### 1. Locate the tree file, reroot on the outgroup if one is set

```bash
run_dir="$RUN_DIR"
tool=$(python3 -c "import json;print(json.load(open('$run_dir/params.json'))['tree_tool'])")
sample=$(python3 -c "import json,os;print(os.path.splitext(os.path.basename(json.load(open('$run_dir/params.json'))['input_fasta']))[0])")

if [ "$tool" = iqtree ]; then
    TREE="$run_dir/trees/${sample}.treefile"
else
    # raxml branch: build/phylo-builder v1.0.0+ produces both FBP and TBE support trees.
    # Default to TBE for annotation purposes (generally more informative for larger trees);
    # pass --support-metric fbp to use the FBP tree instead.
    TREE="$run_dir/trees/${sample}.raxml.supportTBE"
fi
mkdir -p "$run_dir/itol"

cd /path/to/phylogenetics-agent   # skill root, so `pixi run gotree` resolves

OUTGROUP=$(python3 -c "import json; print(json.load(open('$run_dir/params.json')).get('outgroup') or '')")
if [ -n "$OUTGROUP" ]; then
    # substring-match against real tip names, same convention as preflight/qc
    OG_TIPS=$(pixi run gotree stats tips -i "$TREE" | tail -n +2 | cut -f4 | python3 -c "
import sys
outgroup = '$OUTGROUP'.split(',')
tips = [t.strip() for t in sys.stdin if t.strip()]
matched = sorted({t for og in outgroup for t in tips if og.strip() in t})
print('\n'.join(matched))
")
    if [ -n "$OG_TIPS" ]; then
        echo "$OG_TIPS" | pixi run gotree reroot outgroup -i "$TREE" -l - -o "$run_dir/itol/${sample}_rooted.nwk"
        # stderr here is where SP4's non-monophyletic warning shows up, if any
        TREE="$run_dir/itol/${sample}_rooted.nwk"
    else
        echo "WARNING: outgroup '$OUTGROUP' set in params.json but no tip name matched it in $TREE — tree left as-is (not rerooted)." >&2
    fi
fi
```

### 2. Always: generate the italic-label dataset

The script only needs plain `python3` (stdlib only) — it shells out to `gotree` itself via `--gotree-cmd`, so run it from the skill's root directory (where `pixi.toml` lives) so `pixi run gotree` resolves:

```bash
cd /path/to/phylogenetics-agent   # skill root, so `pixi run gotree` resolves
python3 visualize/phylo-itol/scripts/itol_tip_labels.py "$TREE" \
    -o "$run_dir/itol/${sample}_labels.txt" \
    --gotree-cmd "pixi run gotree"
```

### 3. If a group source was given: generate the colorstrip

```bash
# Regex mode (SP1 option A):
python3 visualize/phylo-itol/scripts/itol_colorstrip.py "$TREE" \
    -o "$run_dir/itol/${sample}_colorstrip.txt" \
    --regex '^([A-Za-z]+)_' --label "Genus" \
    --legend-out "$run_dir/itol/${sample}_legend.md" \
    --gotree-cmd "pixi run gotree"

# TSV mode (SP1 option B):
python3 visualize/phylo-itol/scripts/itol_colorstrip.py "$TREE" \
    -o "$run_dir/itol/${sample}_colorstrip.txt" \
    --groups-tsv /path/to/groups.tsv --label "<group label>" \
    --legend-out "$run_dir/itol/${sample}_legend.md" \
    --gotree-cmd "pixi run gotree"
```

## Interpretation Guidelines

- **Labels dataset**: always trivially "correct" — if it's empty, the tree file itself has 0 tips (upstream bug, not this sub-skill's).
- **Colorstrip with 0 unmatched tips**: every tip got a real group — good regex/TSV coverage.
- **Colorstrip with some `unclassified`**: still usable (rendered grey in iTOL), but the legend will show it — route through SP2 if the user cares about full coverage.

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `ERROR: no tips found in <tree>` | Tree file path wrong, or `build/phylo-builder` hasn't produced it yet | Check `checkpoints/tree.done.json`'s `output_files` for the real path. |
| `gotree: command not found` | Script invoked without `--gotree-cmd "pixi run gotree"` outside an activated pixi shell | Always pass `--gotree-cmd`, or run inside `pixi shell`. |
| All tips end up `unclassified` | Regex doesn't match this tip-naming convention at all | Print a few tip names first (`gotree stats tips -i <tree>`) and adjust the regex against real examples before running the full colorstrip. |
| iTOL upload shows the colorstrip but all one grey color | Group names in `DATA` rows don't match any key iTOL recognizes — actually a cosmetic non-issue, iTOL derives the color from the 2nd column directly, not the group name; check the hex codes in the file are valid `#RRGGBB`. |
| Legend group counts don't sum to tip count | Should be impossible (every tip gets exactly one group) — if seen, the TSV had duplicate tip-name rows; the last one silently wins. | Deduplicate the `--groups-tsv` file. |
| `outgroup '<X>' set in params.json but no tip name matched it` | Substring match against `gotree stats tips` found nothing — typo, or the tip was reverse-complemented by mafft `--adjustdirection` upstream and now carries an `_R_` prefix (same gotcha as `prune/phylo-prune` SP2 and `preflight/phylo-preflight` SP7) | Run `gotree stats tips -i <tree>` and match the exact name; the uploaded tree is left unrooted (original topology, arbitrary root) if this isn't fixed. |
| `Warning! The given outgroup is not Monophyloetic` (gotree's own typo, not ours) | The named outgroup taxa don't form a clade in this tree | Route through SP4 — gotree still rerooted at the LCA, but confirm that's the rooting the user actually wants. |

## Verification

- [ ] `$RUN_DIR/itol/<sample>_labels.txt` exists, starts with `TREE_COLORS`.
- [ ] If a colorstrip was requested: `$RUN_DIR/itol/<sample>_colorstrip.txt` exists, starts with `DATASET_COLORSTRIP`, and `<sample>_legend.md` group counts sum to the tree's tip count.
- [ ] If `params.json` has a non-empty `outgroup` that matched a tip: `$RUN_DIR/itol/<sample>_rooted.nwk` exists and `gotree stats tips -i <file>` succeeds; that file (not the original `trees/*` tree) is what gets uploaded to iTOL.

## What NOT to do

- Do **not** hardcode any project-specific taxonomy (e.g. species→complex mappings) into this sub-skill — that belongs in the user's own `--groups-tsv` file, kept outside the skill repo. `phylogenetics-agent` is a general single-marker tree builder, not tied to any one study.
- Do **not** parse the Newick file with a hand-rolled regex — always shell out to `gotree stats tips`, which already handles quoting, escaped characters, and branch-length/support-value ambiguity correctly.

## Handoff

> Visualization complete. `itol/<sample>_labels.txt` written (plus `itol/<sample>_colorstrip.txt` and `itol/<sample>_legend.md` if a colorstrip was requested, and `itol/<sample>_rooted.nwk` if an outgroup was set and matched). Upload the tree file — `<sample>_rooted.nwk` if it exists, otherwise the original `trees/*` file — and these dataset(s) together at https://itol.embl.de/upload.cgi.

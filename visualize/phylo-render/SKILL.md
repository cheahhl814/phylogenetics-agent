---
name: phylo-render
description: 'Render an offline, scriptable publication-format tree figure (SVG/PDF/PNG) from the tree build/phylo-builder produces, using toytree (matplotlib/toyplot-backed, no browser or upload needed). Complements visualize/phylo-itol: use phylo-render for batch/CI-friendly static figures, phylo-itol for interactive annotation with true italic tip labels. Triggers: "render the tree figure", "publication tree image", "export tree as PDF/SVG/PNG", "phylo-render", "toytree".'
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "render the tree figure"
  - "publication tree image"
  - "export tree as PDF"
  - "export tree as SVG"
  - "phylo-render"
  - "toytree"
---

# phylo-render

> **v1.0.0.** Optional visualization phase of `phylogenetics-agent`, run after `qc/phylo-qc`, alongside `visualize/phylo-itol`. Produces a static SVG/PDF/PNG figure directly from the Newick tree — no browser, no upload, scriptable/batch-friendly. Uses [toytree](https://toytree.readthedocs.io) (built on toyplot).

## When to use this vs. `phylo-itol`

| Need | Use |
| --- | --- |
| Interactive exploration, true italic species names, custom colorstrips/heatmaps | `visualize/phylo-itol` (uploads to itol.embl.de) |
| Offline/scriptable figure, CI pipeline, no internet/browser dependency | `phylo-render` (this sub-skill) |
| Both | Run both — they don't conflict, write to different subdirectories |

**Known limitation**: tip labels are **not italicized** in `phylo-render`'s output. This was tested directly: toyplot 2.1.0's CSS-style validator rejects the `font-style` key even though its own PDF (reportlab) renderer has working italic-font-selection code that reads exactly that key — a real inconsistency in the library, not a flag we're missing. If italic species names are required for the figure, use `phylo-itol` instead (iTOL's web renderer supports italics natively) and export from there.

## 0. Inputs / Outputs contract

### Inputs

| Path | Source | Required? |
| --- | --- | --- |
| `$RUN_DIR/checkpoints/tree.done.json` | `build/phylo-builder` | yes |
| the tree file itself | `build/phylo-builder` | yes |

### Outputs

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/figures/<sample>.svg` | SVG | vector, always included by default |
| `$RUN_DIR/figures/<sample>.pdf` | PDF | vector, always included by default |
| `$RUN_DIR/figures/<sample>.png` | PNG | raster, always included by default |

## 0.5 Ask-User Stop Points

### SP1 — No support values found on the tree

| Trigger | Evidence | Action |
| --- | --- | --- |
| Every internal node's `support` field is `NaN` (script prints a warning, not an error) | Wrong tree file passed (e.g. an intermediate/unsupported tree), or the tree genuinely has no support annotation | Ask: "No bootstrap support values found on this tree — figure will render without them. Pick: (A) proceed anyway (topology-only figure), (B) check the tree file path — `checkpoints/tree.done.json`'s `output_files` should point at the support tree, not an unsupported intermediate, (C) abort" |

**Auto-pick when**: support values are present. No ask.

### SP2 — TBE vs. FBP support scale confusion

| Trigger | Evidence | Action |
| --- | --- | --- |
| `tree_tool=raxml` and the user seems to expect 0–100 percentages but the rendered labels show 0–1 decimals | RAxML-NG's TBE metric is on a 0–1 scale; FBP and IQ-TREE's UFBoot are both 0–100 | Ask: "This is the TBE support tree (0–1 scale, not a percentage). Pick: (A) keep TBE, (B) switch to the FBP tree instead (`*.raxml.supportFBP`, 0–100 scale, more directly comparable to IQ-TREE runs), (C) render both" |

**Auto-pick when**: `tree_tool=iqtree`, or the user didn't express a percentage expectation. No ask.

## Procedure

### 1. Locate the tree file

Same logic as `visualize/phylo-itol` step 1 — default to `.treefile` (iqtree) or `.raxml.supportTBE` (raxml branch; use `.raxml.supportFBP` if the user wants the 0–100 scale, per SP2).

### 2. Render

```bash
mkdir -p "$run_dir/figures"
python3 visualize/phylo-render/scripts/render_tree.py "$TREE" \
    -o "$run_dir/figures/${sample}" \
    --formats svg,pdf,png
```

Useful flags: `--no-support-labels` (topology-only), `--no-ladderize`, `--width`/`--height`, `--font-size`.

## Interpretation Guidelines

- **Support values shown, tree ladderized, all 3 formats written**: normal success.
- **Warning "no support values found"**: route to SP1 — likely the wrong tree file was passed.

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: toytree` | pixi env not reinstalled after `toytree` was added to `pixi.toml` | `pixi install`. |
| `ModuleNotFoundError: packaging` (during PNG export specifically) | toyplot's reportlab-based PNG backend needs `packaging`, not pulled in transitively by `toytree` alone | Already pinned in `pixi.toml`; if seen, re-run `pixi install`. |
| `ValueError: Not an allowed CSS style: font-style` | Something (a future edit) tried to pass `tip_labels_style={"font-style": ...}` | Don't — toyplot 2.1.0 rejects it (see Known Limitation above). Use `phylo-itol` for italics instead. |
| Figure looks fine but support labels show `0.xx` instead of a percentage | This is the raxml TBE tree — expected, see SP2 | Switch to `.raxml.supportFBP` if a 0–100 scale is wanted. |
| `WARNING: no support values found` | Wrong tree file, or genuinely unsupported topology | Route to SP1. |
| Figure is very cramped / tip labels overlap | `--height` too small for the tip count | Default height is `28px * ntips` (min 300) — for very large trees, raise `--height` further or drop `--width`. |

## Verification

- [ ] `$RUN_DIR/figures/<sample>.{svg,pdf,png}` all exist.
- [ ] Support labels present unless the user explicitly asked for `--no-support-labels`.

## What NOT to do

- Do **not** try to force italic tip labels via `font-style` or oblique-named `font-family` values — both were tested and fail against toyplot 2.1.0's CSS validator. Point the user to `phylo-itol` instead.
- Do **not** treat TBE and FBP/UFBoot support values as the same scale when comparing runs.

## Handoff

> Render complete. `figures/<sample>.{svg,pdf,png}` written. For interactive exploration or true italic tip labels, also run `visualize/phylo-itol`.

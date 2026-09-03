#!/usr/bin/env python3
"""Render a publication-format tree figure (SVG/PDF/PNG) from a Newick file using toytree.

Offline, scriptable, no browser or upload step — the complement to
visualize/phylo-itol (which produces interactive iTOL annotation datasets
instead of a static figure). Support values are auto-detected from internal
node labels (works with both IQ-TREE ultrafast-bootstrap .treefile and
RAxML-NG .raxml.supportFBP/supportTBE outputs).

--root-outgroup NAME[,NAME...] reroots the tree (toytree's native .root(), no gotree
call) before drawing, substring-matched against tip labels. If the outgroup isn't
monophyletic, falls back to rooting at its MRCA (matching gotree reroot outgroup's
default behavior); if even that fails (e.g. the MRCA is already the tree's root),
warns and leaves the tree as originally rooted rather than crashing.

KNOWN LIMITATION: tip labels are NOT italicized. toyplot 2.1.0's CSS-style
validator rejects `font-style` even though its own PDF renderer supports it
(a real inconsistency in the library, confirmed while building this script —
not a workaround-able flag). If italic species names matter for the figure,
use visualize/phylo-itol instead: upload the tree to itol.embl.de with the
generated label-style dataset, which renders true italics, then export from
there.
"""
import argparse
import sys

import toytree


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("treefile")
    ap.add_argument("-o", "--output-prefix", required=True,
                     help="Output path without extension; each requested format appends its own")
    ap.add_argument("--formats", default="svg,pdf,png",
                     help="Comma-separated: svg,pdf,png (default: all three)")
    ap.add_argument("--width", type=int, default=600)
    ap.add_argument("--height", type=int, default=None,
                     help="Default: scaled from tip count (28px/tip, min 300)")
    ap.add_argument("--no-support-labels", action="store_true",
                     help="Hide internal-node support values")
    ap.add_argument("--no-ladderize", action="store_true",
                     help="Skip ladderizing (sorting clades by size) — off by default means ladderized")
    ap.add_argument("--font-size", default="11px")
    ap.add_argument("--root-outgroup",
                     help="Comma-separated outgroup taxon name(s) -- substring-matched against tip labels, "
                          "then rooted via toytree's native .root() (no gotree call needed here)")
    args = ap.parse_args()

    tree = toytree.tree(args.treefile)
    # toytree's internal-label auto-detection heuristic silently drops raxml-ng's
    # support labels (both .supportFBP and .supportTBE -- verified live against
    # raxml-ng 1.2.0 output), leaving the support feature all-NaN even though the
    # file carries them. If support came up empty, re-parse forcing internal
    # labels into the support feature (same convention IQ-TREE files hit by
    # auto-detection).
    if not tree.get_node_data()["support"].notna().any():
        tree = toytree.tree(args.treefile, internal_labels="support")

    if args.root_outgroup:
        tip_labels = tree.get_tip_labels()
        queries = [q.strip() for q in args.root_outgroup.split(",") if q.strip()]
        matched = sorted({t for q in queries for t in tip_labels if q in t})
        if not matched:
            print(f"WARNING: --root-outgroup '{args.root_outgroup}' matched no tip label — tree left unrooted.", file=sys.stderr)
        else:
            try:
                tree = tree.root(*matched)
            except Exception:
                # toytree hard-errors on a non-monophyletic outgroup (unlike gotree, which
                # warns and reroots at the outgroup's LCA anyway) -- fall back to that same
                # LCA behavior so phylo-render and phylo-itol agree on the rooting.
                try:
                    mrca = tree.get_mrca_node(*matched)
                    tree = tree.root(mrca)
                    print(f"WARNING: outgroup {matched} is not monophyletic — rooted at their common ancestor instead.", file=sys.stderr)
                except Exception as exc:
                    print(f"WARNING: rooting on {matched} failed ({exc}) — tree left as-is.", file=sys.stderr)

    if not args.no_ladderize:
        tree = tree.mod.ladderize()

    height = args.height or max(300, 28 * tree.ntips)

    draw_kwargs = dict(
        tip_labels_style={"font-size": args.font_size},
        width=args.width,
        height=height,
    )
    if not args.no_support_labels:
        node_data = tree.get_node_data()
        if "support" in node_data.columns and node_data["support"].notna().any():
            draw_kwargs["node_labels"] = "support"
            draw_kwargs["node_sizes"] = 10
        else:
            print("WARNING: no support values found on internal nodes — skipping node labels", file=sys.stderr)

    canvas, axes, mark = tree.draw(**draw_kwargs)

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    written = []
    for fmt in formats:
        path = f"{args.output_prefix}.{fmt}"
        if fmt == "svg":
            import toyplot.svg
            toyplot.svg.render(canvas, path)
        elif fmt == "pdf":
            import toyplot.pdf
            toyplot.pdf.render(canvas, path)
        elif fmt == "png":
            import toyplot.png
            toyplot.png.render(canvas, path)
        else:
            print(f"WARNING: unknown format '{fmt}', skipping", file=sys.stderr)
            continue
        written.append(path)

    if not written:
        print("ERROR: no formats rendered", file=sys.stderr)
        sys.exit(1)
    print(f"{tree.ntips} tips -> " + ", ".join(written))


if __name__ == "__main__":
    main()

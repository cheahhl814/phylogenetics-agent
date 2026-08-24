#!/usr/bin/env python3
"""Render a publication-format tree figure (SVG/PDF/PNG) from a Newick file using toytree.

Offline, scriptable, no browser or upload step — the complement to
visualize/phylo-itol (which produces interactive iTOL annotation datasets
instead of a static figure). Support values are auto-detected from internal
node labels (works with both IQ-TREE ultrafast-bootstrap .treefile and
RAxML-NG .raxml.supportFBP/supportTBE outputs).

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
    args = ap.parse_args()

    tree = toytree.tree(args.treefile)
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

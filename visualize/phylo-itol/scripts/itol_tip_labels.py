#!/usr/bin/env python3
"""Generate an iTOL TREE_COLORS dataset that italicizes every tip label.

Tip names are read from `gotree stats tips` output (robust — no Newick
regex parsing), not parsed from the tree file directly.
"""
import argparse
import subprocess
import sys


def get_tips(treefile: str, gotree_cmd: list[str]) -> list[str]:
    result = subprocess.run(
        [*gotree_cmd, "stats", "tips", "-i", treefile],
        capture_output=True, text=True, check=True,
    )
    tips = []
    for line in result.stdout.splitlines()[1:]:  # skip header row
        parts = line.split("\t")
        if len(parts) >= 4:
            tips.append(parts[3])
    return tips


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("treefile")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--font-size", type=int, default=24)
    ap.add_argument("--style", default="italic", choices=["italic", "bold", "bold-italic", "normal"])
    ap.add_argument("--color", default="#000000")
    ap.add_argument("--gotree-cmd", default="gotree",
                     help="Command to invoke gotree, e.g. 'pixi run gotree' (default: gotree)")
    args = ap.parse_args()

    gotree_cmd = args.gotree_cmd.split()
    tips = get_tips(args.treefile, gotree_cmd)
    if not tips:
        print(f"ERROR: no tips found in {args.treefile}", file=sys.stderr)
        sys.exit(1)

    lines = ["TREE_COLORS", "SEPARATOR TAB", "DATA"]
    for tip in tips:
        lines.append(f"{tip}\tlabel\t{args.color}\t{args.style}\t{args.font_size}")

    with open(args.output, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(tips)} tips -> {args.output}")


if __name__ == "__main__":
    main()

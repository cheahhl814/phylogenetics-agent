#!/usr/bin/env python3
"""Generate an iTOL DATASET_COLORSTRIP from a tree plus a tip -> group mapping.

Group source (exactly one required):
  --groups-tsv FILE   two-column TSV: tip_name<TAB>group
  --regex PATTERN     applied to each tip name; the first capture group is
                       the group label (e.g. '^([A-Za-z]+)_' to group by genus)

Colors are auto-assigned deterministically from a fixed categorical palette
(same group -> same color across runs); pass --colors-tsv to override
specific group colors explicitly (group<TAB>#hexcolor).

Tip names come from `gotree stats tips`, not Newick regex parsing.
"""
import argparse
import re
import subprocess
import sys
from collections import Counter

PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]
UNCLASSIFIED_COLOR = "#cccccc"


def get_tips(treefile: str, gotree_cmd: list[str]) -> list[str]:
    result = subprocess.run(
        [*gotree_cmd, "stats", "tips", "-i", treefile],
        capture_output=True, text=True, check=True,
    )
    tips = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 4:
            tips.append(parts[3])
    return tips


def load_groups_tsv(path: str) -> dict:
    mapping = {}
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    return mapping


def group_by_regex(tips: list[str], pattern: str) -> tuple[dict, list[str]]:
    rx = re.compile(pattern)
    mapping, unmatched = {}, []
    for tip in tips:
        m = rx.search(tip)
        if m and m.groups():
            mapping[tip] = m.group(1)
        else:
            unmatched.append(tip)
    return mapping, unmatched


def load_colors_tsv(path: str) -> dict:
    colors = {}
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                colors[parts[0]] = parts[1]
    return colors


def assign_colors(groups: list[str], overrides: dict) -> dict:
    colors = dict(overrides)
    palette_idx = 0
    for g in sorted(set(groups)):
        if g in colors:
            continue
        if g in ("unclassified", "unknown", ""):
            colors[g] = UNCLASSIFIED_COLOR
            continue
        colors[g] = PALETTE[palette_idx % len(PALETTE)]
        palette_idx += 1
    return colors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("treefile")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--label", default="Group", help="DATASET_LABEL shown in iTOL")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--groups-tsv", help="tip_name<TAB>group file")
    src.add_argument("--regex", help="regex applied to tip names; group(1) is the label")
    ap.add_argument("--colors-tsv", help="optional group<TAB>#hexcolor overrides")
    ap.add_argument("--legend-out", help="optional path to write a human-readable legend")
    ap.add_argument("--gotree-cmd", default="gotree")
    args = ap.parse_args()

    gotree_cmd = args.gotree_cmd.split()
    tips = get_tips(args.treefile, gotree_cmd)
    if not tips:
        print(f"ERROR: no tips found in {args.treefile}", file=sys.stderr)
        sys.exit(1)

    if args.groups_tsv:
        raw_map = load_groups_tsv(args.groups_tsv)
        tip_group = {t: raw_map.get(t, "unclassified") for t in tips}
        unmatched = [t for t in tips if t not in raw_map]
    else:
        tip_group, unmatched = group_by_regex(tips, args.regex)
        for t in unmatched:
            tip_group[t] = "unclassified"

    if unmatched:
        print(f"WARNING: {len(unmatched)}/{len(tips)} tips have no group "
              f"(assigned 'unclassified'): {unmatched}", file=sys.stderr)

    overrides = load_colors_tsv(args.colors_tsv) if args.colors_tsv else {}
    colors = assign_colors(list(tip_group.values()), overrides)

    lines = [
        "DATASET_COLORSTRIP", "SEPARATOR TAB",
        f"DATASET_LABEL\t{args.label}", "COLOR\t#ffffff", "", "DATA",
    ]
    for tip in tips:
        g = tip_group[tip]
        lines.append(f"{tip}\t{colors[g]}\t{g}")

    with open(args.output, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(tips)} tips -> {args.output}")

    dist = Counter(tip_group.values())
    legend_lines = [f"# {args.label} legend", ""]
    for g, n in sorted(dist.items()):
        legend_lines.append(f"- `{colors[g]}` **{g}** ({n} tips)")
        print(f"  {g}: {n} ({colors[g]})")

    if args.legend_out:
        with open(args.legend_out, "w") as f:
            f.write("\n".join(legend_lines) + "\n")
        print(f"legend -> {args.legend_out}")


if __name__ == "__main__":
    main()

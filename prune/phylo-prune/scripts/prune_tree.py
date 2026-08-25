#!/usr/bin/env python3
"""Prune a phylogenetics-agent tree down to a curated subset of taxa via `gotree
prune`, preserving branch lengths (gotree sums collapsed-node lengths correctly)
and support values. No hand-rolled Newick parsing -- gotree already handles the
IQ-TREE .contree / .treefile support-before-colon convention.

Modes (pick exactly one):
  --keep NAME [NAME ...]     keep only these tips
  --keep-file FILE           keep only tips listed in FILE (one per line)
  --exclude-file FILE        remove tips listed in FILE (one per line)
  --reference-tree FILE      keep only tips also present in this Newick file

Requires gotree on PATH (or pass --gotree-cmd, e.g. "pixi run gotree").
"""
import argparse
import subprocess
import sys


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def list_tips(gotree_argv: list[str], tree: str) -> list[str]:
    result = run(gotree_argv + ["stats", "tips", "-i", tree])
    if result.returncode != 0:
        print(f"ERROR: gotree stats tips failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = result.stdout.strip().splitlines()[1:]  # drop header
    return [line.split("\t")[3] for line in lines if line.strip()]


def read_names(path: str) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tree", help="input Newick tree (.treefile, .contree, .supportTBE/.supportFBP, etc.)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--keep", nargs="+", metavar="NAME")
    mode.add_argument("--keep-file", metavar="FILE")
    mode.add_argument("--exclude-file", metavar="FILE")
    mode.add_argument("--reference-tree", metavar="FILE")
    ap.add_argument("-o", "--output", required=True, help="pruned Newick output path")
    ap.add_argument("--report-out", help="text report path (default: <output>.report.txt)")
    ap.add_argument("--gotree-cmd", default="gotree", help='e.g. "pixi run gotree"')
    ap.add_argument("--force", action="store_true", help="proceed even if some requested names are not in the tree")
    args = ap.parse_args()

    gotree = args.gotree_cmd.split()
    report_out = args.report_out or f"{args.output}.report.txt"

    original_tips = set(list_tips(gotree, args.tree))
    n_before = len(original_tips)

    cmd = gotree + ["prune", "-i", args.tree, "-o", args.output]
    requested = None
    if args.keep:
        requested = set(args.keep)
        cmd += ["-r"] + args.keep
    elif args.keep_file:
        requested = set(read_names(args.keep_file))
        cmd += ["-f", args.keep_file, "-r"]
    elif args.exclude_file:
        requested = set(read_names(args.exclude_file))
        cmd += ["-f", args.exclude_file]
    elif args.reference_tree:
        cmd += ["-c", args.reference_tree]

    # gotree silently ignores keep/exclude names that don't exist in the source
    # tree instead of erroring -- check ourselves before running.
    missing = sorted(n for n in requested if n not in original_tips) if requested else []
    if missing and not args.force:
        print(
            f"ERROR: {len(missing)} requested name(s) not found in {args.tree}: "
            f"{', '.join(missing)}\n"
            "This is often a strand-flip artifact -- if mafft --adjustdirection "
            "flipped this tip upstream, its tree name carries an '_R_' prefix.\n"
            "Re-run with --force to proceed anyway (missing names are simply ignored).",
            file=sys.stderr,
        )
        sys.exit(1)

    result = run(cmd)
    if result.returncode != 0:
        if "only made of two tips" in result.stderr or "only made of one tip" in result.stderr:
            print(
                f"ERROR: the requested keep/exclude set leaves too few tips "
                f"(gotree refuses to produce a tree with < 3 tips).\n{result.stderr}",
                file=sys.stderr,
            )
        else:
            print(f"ERROR: gotree prune failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    pruned_tips = set(list_tips(gotree, args.output))
    n_after = len(pruned_tips)
    removed = sorted(original_tips - pruned_tips)

    with open(report_out, "w") as f:
        f.write(f"tips before: {n_before}\n")
        f.write(f"tips after:  {n_after}\n")
        f.write(f"removed ({len(removed)}): {', '.join(removed) if removed else '(none)'}\n")
        if missing:
            f.write(f"requested but not found in source tree ({len(missing)}): {', '.join(missing)}\n")

    print(f"Pruned {n_before} -> {n_after} tips. Wrote {args.output} and {report_out}")


if __name__ == "__main__":
    main()

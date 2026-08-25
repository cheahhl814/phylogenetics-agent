#!/usr/bin/env python3
"""Compute phylogenetics-agent QC metrics and automated result-interpretation
flags from a finished tree, then write qc-report.md.

Uses `gotree stats edges` (length + support + terminal + topodepth per branch)
and `gotree stats monophyletic` -- no hand-rolled Newick support-regex, and no
new dependency (gotree is already a pipeline requirement).

Automated interpretation, beyond the plain mean/min bootstrap number:
  - weak clades: internal edges below --support-threshold, with clade size
  - long-branch outliers: terminal edges whose length is a MAD-based outlier
    (classic signal for a misidentified/contaminant sequence or alignment
    artifact -- see prune/phylo-prune to drop a flagged tip)
  - outgroup monophyly: if params.json names an outgroup, checks it actually
    forms a monophyletic group outside the ingroup
"""
import argparse
import json
import statistics
import subprocess
import sys
import tempfile


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def gotree_edges(gotree: list[str], tree: str) -> list[dict]:
    result = run(gotree + ["stats", "edges", "-i", tree])
    if result.returncode != 0:
        print(f"ERROR: gotree stats edges failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = result.stdout.strip().splitlines()
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        rows.append(dict(zip(header, line.split("\t"))))
    return rows


def gotree_tips(gotree: list[str], tree: str) -> list[str]:
    result = run(gotree + ["stats", "tips", "-i", tree])
    if result.returncode != 0:
        print(f"ERROR: gotree stats tips failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = result.stdout.strip().splitlines()[1:]
    return [line.split("\t")[3] for line in lines if line.strip()]


def gotree_monophyletic(gotree: list[str], tree: str, tip_names: list[str]) -> bool | None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(tip_names) + "\n")
        tipfile = f.name
    result = run(gotree + ["stats", "monophyletic", "-i", tree, "-l", tipfile])
    if result.returncode != 0:
        print(f"WARNING: gotree stats monophyletic failed:\n{result.stderr}", file=sys.stderr)
        return None
    lines = result.stdout.strip().splitlines()
    if len(lines) < 2:
        return None
    return lines[1].split("\t")[1].strip().lower() == "true"


def mad_outliers(values: dict[str, float], k: float) -> list[tuple[str, float]]:
    """Return (name, value) pairs whose value exceeds median + k*MAD, sorted desc."""
    if len(values) < 4:
        return []  # too few tips for MAD to mean anything
    lens = list(values.values())
    med = statistics.median(lens)
    mad = statistics.median(abs(v - med) for v in lens)
    if mad == 0:
        return []
    threshold = med + k * mad * 1.4826  # 1.4826 scales MAD to be consistent with stdev under normality
    return sorted(((n, v) for n, v in values.items() if v > threshold), key=lambda x: -x[1])


def fasta_seq_count(path: str) -> int:
    with open(path) as f:
        return sum(1 for line in f if line.startswith(">"))


def fasta_first_seq_len(path: str) -> int:
    length = 0
    started = False
    with open(path) as f:
        for line in f:
            if line.startswith(">"):
                if started:
                    break
                started = True
                continue
            if started:
                length += len(line.strip())
    return length


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tree", help="support tree (.treefile, .raxml.supportTBE/FBP, etc.)")
    ap.add_argument("--trimmed-aln", required=True, help="post-trimal FASTA")
    ap.add_argument("--raw-aln", help="pre-trim alignment FASTA (optional, for raw length reporting)")
    ap.add_argument("--params", required=True, help="params.json from preflight")
    ap.add_argument("--ascii-tree", help="path to the gotree ASCII render (.tree.txt), embedded verbatim if given")
    ap.add_argument("-o", "--output", required=True, help="qc-report.md path")
    ap.add_argument("--gotree-cmd", default="gotree", help='e.g. "pixi run gotree"')
    ap.add_argument("--support-threshold", type=float, default=70.0)
    ap.add_argument("--mad-k", type=float, default=3.0, help="MAD multiplier for long-branch outlier detection")
    args = ap.parse_args()

    gotree = args.gotree_cmd.split()
    params = json.load(open(args.params))

    edges = gotree_edges(gotree, args.tree)

    terminal_lengths = {}
    internal_supports = []  # (support, topodepth)
    for e in edges:
        length = float(e["length"]) if e.get("length") not in (None, "", "N/A") else None
        if e["terminal"] == "true":
            if length is not None and e.get("rightname"):
                terminal_lengths[e["rightname"]] = length
        else:
            support = e.get("support")
            if support not in (None, "", "N/A"):
                internal_supports.append((float(support), int(e.get("topodepth", 0))))

    mean_support = statistics.mean(s for s, _ in internal_supports) if internal_supports else None
    min_support = min((s for s, _ in internal_supports), default=None)
    weak_clades = sorted(
        [(s, n) for s, n in internal_supports if s < args.support_threshold], key=lambda x: x[0]
    )
    long_branch_outliers = mad_outliers(terminal_lengths, args.mad_k)

    outgroup = (params.get("outgroup") or "").strip()
    outgroup_monophyletic = None
    outgroup_matched_tips = []
    if outgroup:
        all_tips = gotree_tips(gotree, args.tree)
        for taxon in [t.strip() for t in outgroup.split(",") if t.strip()]:
            outgroup_matched_tips += [t for t in all_tips if taxon in t]
        outgroup_matched_tips = sorted(set(outgroup_matched_tips))
        if outgroup_matched_tips:
            outgroup_monophyletic = gotree_monophyletic(gotree, args.tree, outgroup_matched_tips)

    n_taxa = fasta_seq_count(args.trimmed_aln)
    trimmed_len = max((fasta_first_seq_len(args.trimmed_aln),), default=0)
    raw_len = fasta_first_seq_len(args.raw_aln) if args.raw_aln else None

    flags = []
    if mean_support is not None and mean_support < args.support_threshold:
        flags.append(f"Mean bootstrap support {mean_support:.1f}% is below the {args.support_threshold:.0f}% usability threshold.")
    if weak_clades:
        flags.append(f"{len(weak_clades)} internal clade(s) below {args.support_threshold:.0f}% support (see table).")
    if long_branch_outliers:
        names = ", ".join(n for n, _ in long_branch_outliers)
        flags.append(f"{len(long_branch_outliers)} long-branch outlier tip(s) detected: {names}.")
    if outgroup_monophyletic is False:
        flags.append(f"Outgroup ({', '.join(outgroup_matched_tips)}) is NOT monophyletic -- check outgroup choice or the tree topology.")

    verdict = "GO-WITH-WARNINGS" if flags else "GO"

    lines = []
    lines.append("# phylogenetics-agent QC report\n")
    lines.append(f"Run:        {args.params.rsplit('/params.json', 1)[0]}")
    lines.append("Pipeline:   phylogenetics-agent v1.0.0\n")
    lines.append("## Overall verdict\n")
    lines.append(f"**{verdict}** {'✅' if verdict == 'GO' else '⚠️'}\n")
    lines.append("## Run configuration\n")
    lines.append("| Param | Value |")
    lines.append("|---|---|")
    lines.append(f"| Aligner | {params.get('aligner', '')} |")
    lines.append(f"| Tree tool | {params.get('tree_tool', '')} |")
    lines.append(f"| Model | {params.get('model') or 'ModelFinder (iqtree)'} |")
    lines.append(f"| Bootstrap replicates | {params.get('bootstrap_replicates', '')} |")
    lines.append(f"| Outgroup | {outgroup or 'none -- unrooted'} |\n")
    lines.append("## Metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Taxa | {n_taxa} |")
    if raw_len is not None:
        lines.append(f"| Raw alignment length | {raw_len} bp/aa |")
    lines.append(f"| Trimmed alignment length | {trimmed_len} bp/aa |")
    lines.append(f"| Mean bootstrap support (internal nodes) | {mean_support:.1f}% |" if mean_support is not None else "| Mean bootstrap support (internal nodes) | N/A |")
    lines.append(f"| Min bootstrap support | {min_support:.1f}% |" if min_support is not None else "| Min bootstrap support | N/A |")
    lines.append("")
    lines.append("## Automated interpretation\n")
    if not flags:
        lines.append("No flags raised -- tree passes all automated checks.\n")
    else:
        for f in flags:
            lines.append(f"- ⚠️ {f}")
        lines.append("")
    if weak_clades:
        lines.append("### Weakly-supported clades\n")
        lines.append("| Support % | Clade size (tips) |")
        lines.append("|---|---|")
        for s, n in weak_clades:
            lines.append(f"| {s:.1f} | {n} |")
        lines.append("")
    if long_branch_outliers:
        lines.append(f"### Long-branch outliers (> median + {args.mad_k:.1f} MAD)\n")
        lines.append("| Tip | Branch length |")
        lines.append("|---|---|")
        for n, v in long_branch_outliers:
            lines.append(f"| {n} | {v:.4f} |")
        lines.append("")
    if outgroup_matched_tips:
        lines.append(f"### Outgroup monophyly\n")
        lines.append(f"Outgroup tips: {', '.join(outgroup_matched_tips)}  ")
        lines.append(f"Monophyletic: **{outgroup_monophyletic}**\n")
    if args.ascii_tree:
        lines.append("## Tree (ASCII render)\n")
        lines.append("```")
        try:
            lines.append(open(args.ascii_tree).read().rstrip())
        except FileNotFoundError:
            lines.append("(ASCII render not found)")
        lines.append("```\n")
    lines.append("## Reproducibility\n")
    lines.append(f"- params.json: {args.params}")
    lines.append(f"- this report: {args.output} (regenerable via this script)")

    with open(args.output, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {args.output}. Verdict: {verdict}. {len(flags)} flag(s) raised.")


if __name__ == "__main__":
    main()

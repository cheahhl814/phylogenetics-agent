#!/usr/bin/env python3
"""Extract a single marker region (16S, COI, Cytb, etc.) from a multi-taxon
mitogenome FASTA via BLASTN against a reference marker sequence, so the
result can be used as phylogenetics-agent's normal single-marker input_fasta.

Generalizes the BLAST-hit-extraction core of the project-local
blast_extract_cds.py (which does full mitogenome annotation -- 13 PCGs + 2
rRNAs + 22 tRNAs + D-loop via a reference GFF/GenBank and tRNAscan-SE) down
to: one marker, one BLASTN pass against a *multi-taxon* target FASTA (not a
single genome), best hit per taxon, strand-corrected extraction. No
annotation output (GFF3/BED), no tRNAscan-SE, no D-loop detection -- this
skill only needs the one marker region per taxon for a single-marker tree.

Direction contract: the reference marker sequence(s) (NCBI-fetched or
user-supplied -- usually partial marker records) are the BLASTN *query*;
the user's multi-taxon mitogenome FASTA is the BLASTN *database*. Target
regions are always extracted FROM the user's own mitogenomes -- never the
reverse (never cut the reference out of NCBI genomes and treat the user's
sequences as the reference).

Reference marker sequence(s) come from one of:
  --marker-ref FILE            user-supplied FASTA (1+ sequences)
  --fetch-marker-ref-taxon T   auto-fetch one sequence via NCBI esearch/efetch
                                (mirrors preflight/phylo-taxon-sampling's
                                fetch_gb_records/parse_gb_record, duplicated
                                here rather than imported across sub-skill
                                directories; primary GenBank submissions only --
                                RefSeq records are excluded)

Requires blastn/makeblastdb on PATH (or pass --blastn-cmd/--makeblastdb-cmd,
e.g. "pixi run blastn").
"""
import argparse
import re
import subprocess
import sys
import tempfile

REFSEQ_PREFIX_RE = re.compile(r"^[A-Z]{2}_")


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def run_piped(argv_list: list[list[str]]) -> str:
    procs = []
    prev_stdout = None
    for i, argv in enumerate(argv_list):
        p = subprocess.Popen(argv, stdin=prev_stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if prev_stdout is not None:
            prev_stdout.close()
        prev_stdout = p.stdout
        procs.append(p)
    out, err = procs[-1].communicate()
    for p in procs[:-1]:
        p.wait()
    if procs[-1].returncode != 0:
        print(f"WARNING: pipeline failed: {argv_list}\n{err}", file=sys.stderr)
        return ""
    return out


def read_fasta(path: str) -> dict[str, str]:
    seqs, name, parts = {}, None, []
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if name is not None:
                    seqs[name] = "".join(parts)
                name = line[1:].split()[0]
                parts = []
            elif name is not None:
                parts.append(line)
    if name is not None:
        seqs[name] = "".join(parts)
    return seqs


def reverse_complement(seq: str) -> str:
    return seq.translate(str.maketrans("ACGTacgtNn", "TGCAtgcaNn"))[::-1]


def fetch_reference(taxon: str, marker: str, esearch_cmd: list[str], efetch_cmd: list[str]) -> tuple[str, str] | None:
    """Mirrors taxon_sampling.py's fetch_gb_records/parse_gb_record, trimmed to
    just what's needed here: one best (longest) primary-submission hit.
    RefSeq records are excluded (NOT srcdb_refseq[PROP] + post-fetch guard),
    matching the primary-submission-only rule shared with
    phylo-taxon-sampling and mitotree-agent."""
    query = f'"{marker}"[Title] AND "{taxon}"[Organism] NOT srcdb_refseq[PROP]'
    text = run_piped([
        [*esearch_cmd, "-db", "nucleotide", "-query", query],
        [*efetch_cmd, "-format", "gb", "-start", "1", "-stop", "5"],
    ])
    records = [rec for rec in re.split(r"\n//\n", text) if rec.strip()]
    candidates = []
    for rec in records:
        locus_m = re.search(r"^LOCUS\s+(\S+)\s+(\d+)\s+bp", rec, re.MULTILINE)
        if not locus_m:
            continue
        accession, length = locus_m.group(1), int(locus_m.group(2))
        origin_m = re.search(r"^ORIGIN.*?\n(.*)", rec, re.DOTALL | re.MULTILINE)
        seq = re.sub(r"[\d\s]", "", origin_m.group(1)).upper() if origin_m else ""
        if not seq:
            continue
        is_refseq = bool(REFSEQ_PREFIX_RE.match(accession))
        candidates.append((1 if is_refseq else 0, -length, accession, seq))  # refseq never selected
    if not candidates:
        return None
    candidates = [c for c in candidates if c[0] == 0]  # primary submissions only
    if not candidates:
        return None
    candidates.sort()
    _, _, accession, seq = candidates[0]
    return accession, seq


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target_fasta", help="multi-taxon mitogenome FASTA (one sequence per taxon)")
    ref_group = ap.add_mutually_exclusive_group(required=True)
    ref_group.add_argument("--marker-ref", help="reference marker FASTA (1+ sequences)")
    ref_group.add_argument("--fetch-marker-ref-taxon", help='taxon name to auto-fetch a reference from, e.g. "Homo sapiens"')
    ap.add_argument("--marker", help='marker name, required with --fetch-marker-ref-taxon, e.g. "16S ribosomal RNA"')
    ap.add_argument("-o", "--output", required=True, help="output marker FASTA, one sequence per taxon with a hit")
    ap.add_argument("--report-out", help="text report path (default: <output>.report.txt)")
    ap.add_argument("--evalue", default="1e-10")
    ap.add_argument("--min-length-frac", type=float, default=0.5, help="flag a hit shorter than this fraction of its matched reference's length")
    ap.add_argument("--max-length-frac", type=float, default=1.5, help="flag a hit longer than this fraction of its matched reference's length")
    ap.add_argument("--blastn-cmd", default="blastn", help='e.g. "pixi run blastn"')
    ap.add_argument("--makeblastdb-cmd", default="makeblastdb", help='e.g. "pixi run makeblastdb"')
    ap.add_argument("--esearch-cmd", default="esearch")
    ap.add_argument("--efetch-cmd", default="efetch")
    args = ap.parse_args()

    blastn = args.blastn_cmd.split()
    makeblastdb = args.makeblastdb_cmd.split()
    report_out = args.report_out or f"{args.output}.report.txt"

    if args.fetch_marker_ref_taxon and not args.marker:
        print("ERROR: --marker is required with --fetch-marker-ref-taxon", file=sys.stderr)
        sys.exit(1)

    target_seqs = read_fasta(args.target_fasta)
    if not target_seqs:
        print(f"ERROR: no sequences found in {args.target_fasta}", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="phylo_mito_extract_") as tmpdir:
        ref_fasta = f"{tmpdir}/ref.fasta"
        if args.marker_ref:
            ref_seqs = read_fasta(args.marker_ref)
            if not ref_seqs:
                print(f"ERROR: no sequences found in {args.marker_ref}", file=sys.stderr)
                sys.exit(1)
        else:
            fetched = fetch_reference(args.fetch_marker_ref_taxon, args.marker, args.esearch_cmd.split(), args.efetch_cmd.split())
            if not fetched:
                print(f"ERROR: no NCBI hit for '{args.marker}' in taxon '{args.fetch_marker_ref_taxon}'", file=sys.stderr)
                sys.exit(1)
            accession, seq = fetched
            ref_seqs = {accession: seq}
            print(f"Auto-fetched reference: {accession} ({len(seq)} bp) for '{args.marker}' in '{args.fetch_marker_ref_taxon}' -- CONFIRM this is the right marker/species before trusting the extraction.")

        with open(ref_fasta, "w") as f:
            for name, seq in ref_seqs.items():
                f.write(f">{name}\n{seq}\n")

        db = f"{tmpdir}/target_db"
        mdb = run(makeblastdb + ["-in", args.target_fasta, "-dbtype", "nucl", "-out", db])
        if mdb.returncode != 0:
            print(f"ERROR: makeblastdb failed:\n{mdb.stderr}", file=sys.stderr)
            sys.exit(1)

        bn = run(blastn + [
            "-task", "blastn", "-query", ref_fasta, "-db", db,
            "-outfmt", "6 qseqid sseqid sstart send pident length bitscore",
            "-evalue", args.evalue, "-max_target_seqs", str(len(target_seqs)),
        ])
        if bn.returncode != 0:
            print(f"ERROR: blastn failed:\n{bn.stderr}", file=sys.stderr)
            sys.exit(1)

    best_hit = {}  # taxon -> (bitscore, qseqid, sstart, send)
    for line in bn.stdout.strip().splitlines():
        if not line.strip():
            continue
        qseqid, sseqid, sstart, send, pident, length, bitscore = line.split("\t")
        bitscore = float(bitscore)
        if sseqid not in best_hit or bitscore > best_hit[sseqid][0]:
            best_hit[sseqid] = (bitscore, qseqid, int(sstart), int(send))

    no_hit = sorted(set(target_seqs) - set(best_hit))
    length_outliers = []
    written = []
    with open(args.output, "w") as f:
        for taxon in target_seqs:
            if taxon not in best_hit:
                continue
            _, ref_name, sstart, send, = best_hit[taxon]
            rev = sstart > send
            lo, hi = (send, sstart) if rev else (sstart, send)
            seq = target_seqs[taxon][lo - 1: hi]
            if rev:
                seq = reverse_complement(seq)
            ref_len = len(ref_seqs[ref_name])
            frac = len(seq) / ref_len if ref_len else 0
            if not (args.min_length_frac <= frac <= args.max_length_frac):
                length_outliers.append((taxon, len(seq), ref_len, frac))
            f.write(f">{taxon}\n{seq}\n")
            written.append(taxon)

    with open(report_out, "w") as f:
        f.write(f"taxa in input: {len(target_seqs)}\n")
        f.write(f"taxa with a marker hit: {len(written)}\n")
        f.write(f"taxa with no hit ({len(no_hit)}): {', '.join(no_hit) if no_hit else '(none)'}\n")
        if length_outliers:
            f.write(f"length outliers ({len(length_outliers)}, outside [{args.min_length_frac}, {args.max_length_frac}] x reference length):\n")
            for taxon, extracted_len, ref_len, frac in length_outliers:
                f.write(f"  {taxon}: {extracted_len} bp extracted vs {ref_len} bp reference ({frac:.2f}x)\n")

    print(f"Extracted {len(written)}/{len(target_seqs)} taxa -> {args.output}. "
          f"{len(no_hit)} no-hit, {len(length_outliers)} length outlier(s). See {report_out}")


if __name__ == "__main__":
    main()

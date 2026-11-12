---
name: phylo-mito-extract
description: 'Extract a single marker region (16S, COI, Cytb, etc.) from a multi-taxon mitogenome FASTA via BLASTN against a reference marker sequence, so the result can be used as phylogenetics-agent normal single-marker input. Not full mitogenome annotation (no tRNAscan-SE, no D-loop, no GFF3/BED) -- just the one marker per taxon. Triggers: "extract 16S from mitogenome", "extract COI from mitogenome", "marker extraction", "mitogenome to marker sequences", "phylo-mito-extract".'
version: 1.1.0
updated: "2026-09-08"
triggers:
  - "extract 16S from mitogenome"
  - "extract COI from mitogenome"
  - "marker extraction"
  - "mitogenome to marker sequences"
  - "phylo-mito-extract"
disable-model-invocation: true
---

# phylo-mito-extract

> **v1.1.0.** Optional pre-preflight stage of `phylogenetics-agent`, run *before* `preflight/phylo-preflight` when the input is whole mitogenome sequences but the tree should be built from a single marker. Generalizes the BLAST-hit-extraction core of the project-local `blast_extract_cds.py` (full mitogenome annotation: 13 PCGs + 2 rRNAs + 22 tRNAs + D-loop, via a reference GFF/GenBank and tRNAscan-SE) down to one marker, extracted from a *multi-taxon* target FASTA in one BLASTN pass -- no annotation output, no tRNAscan-SE, no D-loop detection.
>
> **Direction contract (v1.1.0):** the reference marker sequence(s) — NCBI-fetched (usually partial marker records, primary GenBank submissions only since v1.1.0: RefSeq excluded) or user-supplied — are always the BLASTN **query**; the user's multi-taxon mitogenome FASTA is always the BLASTN **database**. Target regions are extracted FROM the user's own mitogenomes, never the reverse. BLASTN runs with `-task blastn` (not the `megablast` default) so divergent partial references still hit — verified live: a 94%-identity reference with mutations every ~15 bp was invisible to megablast but found immediately by `-task blastn`.

## When to Use This Skill

Use *before* `preflight/phylo-preflight`, when:
- The input FASTA is whole (or partial) mitogenome sequences, one per taxon, but the goal is a single-marker tree (16S, COI, Cytb, 12S, etc.), not a phylogenomic/concatenated analysis.
- A reference sequence for the target marker is available (user-supplied) or can be fetched from NCBI for a related/type species.

Do NOT use this to annotate a mitogenome for its own sake (gene order, full gene set, tRNAs, D-loop) — use the project-local `blast_extract_cds.py` for that. This skill only pulls out the one region needed for a single-marker tree.

Do NOT use if the input FASTA already contains just the marker sequences — go straight to `preflight/phylo-preflight`.

## 0. Inputs / Outputs contract

### Inputs

| Path | Source | Required? |
| --- | --- | --- |
| Multi-taxon mitogenome FASTA (one sequence per taxon) | User | yes |
| Reference marker sequence: `--marker-ref FILE` (user FASTA) OR `--fetch-marker-ref-taxon NAME` + `--marker "16S ribosomal RNA"` (NCBI auto-fetch) | User | exactly one |

### Outputs

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/mito_extract/marker.fasta` | FASTA | One sequence per taxon that had a BLAST hit — becomes `input_fasta` for `preflight/phylo-preflight` |
| `$RUN_DIR/mito_extract/marker.fasta.report.txt` | Text | Taxa with no hit, length-outlier taxa vs. the reference |

## 0.5 Ask-User Stop Points

### SP1 — No reference marker source given

| Trigger | Evidence | Action |
| --- | --- | --- |
| User wants marker extraction but gave neither `--marker-ref` nor `--fetch-marker-ref-taxon` | No default reference makes sense — BLASTN needs a query | Ask: "How should I get a reference `<marker>` sequence? (A) I have a FASTA file with one or more reference sequences, (B) auto-fetch one from NCBI for a named taxon (e.g. a well-annotated relative or type species)" |

**Auto-pick when**: the user already supplied one or the other. No ask.

### SP2 — Auto-fetched reference needs confirmation

| Trigger | Evidence | Action |
| --- | --- | --- |
| `--fetch-marker-ref-taxon` was used (script prints `Auto-fetched reference: <accession> ... CONFIRM this is the right marker/species before trusting the extraction`) | The fetch takes NCBI's best/longest hit for the given taxon+marker query without any manual curation — could be mislabeled, a partial sequence, or the wrong gene if the marker name is ambiguous in NCBI titles | Ask: "Auto-fetched `<accession>` (`<N>` bp) as the `<marker>` reference for `<taxon>`. Pick: (A) accept and proceed, (B) I'll supply my own `--marker-ref` FASTA instead, (C) show me the record first" |

**Auto-pick when**: `--marker-ref` was used (no auto-fetch happened). No ask.

### SP3 — Taxa with no BLAST hit

| Trigger | Evidence | Action |
| --- | --- | --- |
| `extract_marker.py`'s report lists taxa under "no hit" | Either that taxon's mitogenome doesn't carry the marker in a way BLASTN's default evalue can detect (too divergent from the reference, or the marker/mitogenome pair is Just wrong for that taxon), or it's a genuine data problem | Ask: "`<N>` taxa produced no BLAST hit for the marker: `<names>`. Pick: (A) proceed without them (they simply won't be in the tree), (B) supply a closer/second reference sequence and re-run (a single divergent reference can miss distant taxa — verified live: an 85%-identity-capable reference missed a >55%-truncated, more distant-taxon fragment that a same-species reference caught cleanly), (C) lower `--evalue`'s stringency (rarely the real fix — a missing hit is usually a reference-divergence issue, not a threshold issue)" |

**Auto-pick when**: zero no-hit taxa. No ask.

### SP4 — Length-outlier extraction

| Trigger | Evidence | Action |
| --- | --- | --- |
| `extract_marker.py`'s report lists a taxon under "length outliers" (extracted length outside `[--min-length-frac, --max-length-frac] × reference length`, default `[0.5, 1.5]`) | The BLAST hit region for that taxon is unexpectedly short or long relative to the reference — a partial/degraded mitogenome sequence, a pseudogene, or a reference/target mismatch (verified live: a genuinely truncated input correctly triggers this at the expected fraction) | Ask: "`<taxon>` extracted at `<frac>`x the reference length (`<N>` bp vs `<M>` bp). Pick: (A) accept as-is (may be a genuinely partial mitogenome sequence, common in older GenBank submissions), (B) exclude this taxon, (C) inspect the source record before deciding" |

**Auto-pick when**: zero length outliers. No ask.

## Procedure

### 1. Marker-ref supplied by the user

```bash
mkdir -p "$RUN_DIR/mito_extract"
cd /path/to/phylogenetics-agent   # skill root, so `pixi run blastn` resolves

python3 preflight/phylo-mito-extract/scripts/extract_marker.py "$MITOGENOME_FASTA" \
    --marker-ref /path/to/reference_16S.fasta \
    -o "$RUN_DIR/mito_extract/marker.fasta" \
    --blastn-cmd "pixi run blastn" \
    --makeblastdb-cmd "pixi run makeblastdb"
```

### 2. Auto-fetch a reference from NCBI (SP1 option B)

```bash
python3 preflight/phylo-mito-extract/scripts/extract_marker.py "$MITOGENOME_FASTA" \
    --fetch-marker-ref-taxon "Homo sapiens" --marker "16S ribosomal RNA" \
    -o "$RUN_DIR/mito_extract/marker.fasta" \
    --blastn-cmd "pixi run blastn" \
    --makeblastdb-cmd "pixi run makeblastdb" \
    --esearch-cmd "pixi run esearch" --efetch-cmd "pixi run efetch"
# Route the printed "Auto-fetched reference: ..." line through SP2 before trusting the result.
```

### 3. Report to the user, hand off

Read `$RUN_DIR/mito_extract/marker.fasta.report.txt`, route no-hit taxa through SP3 and length outliers through SP4, then point `preflight/phylo-preflight` at `$RUN_DIR/mito_extract/marker.fasta` as its `input_fasta`.

## Interpretation Guidelines

- **All taxa extracted, 0 no-hit, 0 length outliers**: clean extraction — proceed straight to `preflight/phylo-preflight`.
- **Some no-hit taxa**: route through SP3 — usually a reference-divergence issue (verified live: same-species/close-relative references catch cases a distant reference misses), not something to fix by relaxing `--evalue`.
- **Length outliers**: route through SP4 — often a genuinely partial mitogenome record, not a bug in this extraction.

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `ERROR: makeblastdb failed` | Target FASTA malformed, or `blastn`/`makeblastdb` invoked without `--blastn-cmd`/`--makeblastdb-cmd "pixi run ..."` outside an activated pixi shell | Always pass both `--*-cmd` flags, or run inside `pixi shell`. |
| First invocation after adding `blast` to `pixi.toml` hangs for 10+ minutes on a tiny input | `pixi run` was resolving/downloading the new dependency on the fly instead of using an already-installed env (verified live: same command completed in <1s once `pixi install` had been run first) | Run `pixi install` once after any `pixi.toml` change, before invoking `pixi run blastn`/`makeblastdb` in a script. |
| `ERROR: no NCBI hit for '<marker>' in taxon '<taxon>'` | The marker name doesn't match NCBI's title wording for that species, or the taxon name is misspelled | Try a broader/alternate marker phrasing (e.g. `"16S"` vs `"16S ribosomal RNA"`), or switch to `--marker-ref` with a manually-sourced sequence. |
| A taxon known to carry the marker still shows up under "no hit" | A single reference sequence is often too divergent from a distant target taxon for BLASTN's default seeding to find a significant hit (verified live: reference from one bacterial phylum missed even a 40%-length fragment from a different phylum that a same-genus reference caught easily) | Route through SP3 option B — supply a closer reference, not a laxer `--evalue`. |
| Extracted sequences are much shorter than expected across the board | The reference sequence itself is short/partial (BLASTN hit length is capped near the reference query's length, by design — the extraction follows the reference's marker boundaries, not the full homologous region in the target) | Use a full-length reference sequence for the marker, not a fragment. |
| `--marker is required with --fetch-marker-ref-taxon` | `--marker` omitted alongside `--fetch-marker-ref-taxon` | Both are required together; `--marker-ref` mode doesn't need `--marker` at all. |

## Verification

- [ ] `$RUN_DIR/mito_extract/marker.fasta` exists and has ≥ 4 sequences (phylo-preflight's own minimum).
- [ ] Report's "taxa with a marker hit" count matches expectations; no-hit/length-outlier taxa routed through SP3/SP4.
- [ ] If `--fetch-marker-ref-taxon` was used: the auto-fetch was confirmed via SP2 before trusting downstream results.

## What NOT to do

- Do **not** treat this as a general mitogenome annotator — it extracts exactly one marker per taxon, nothing else. For full gene-set annotation (PCGs + rRNAs + tRNAs + D-loop with GFF3/BED output), use the project-local `blast_extract_cds.py` instead.
- Do **not** silently proceed past SP2 (unconfirmed auto-fetched reference) — a wrong species/gene reference produces a plausible-looking but biologically wrong marker FASTA, and nothing downstream would catch it until the tree itself looks wrong.
- Do **not** try to "fix" a no-hit taxon by relaxing `--evalue` before checking whether the reference is simply too divergent (SP3) — verified live that reference choice, not threshold, is the usual actual cause.
- Do **not** omit `-task blastn` from the BLASTN call — the default `megablast` task silently misses divergent partial references (verified live: a 94%-identity reference with mutations every ~15 bp had no 28-mer seed and returned zero hits under megablast, but hit immediately with `-task blastn`; same fix as `mitotree-agent`'s `blast_extract_genes.py`).
- Do **not** reverse the extraction direction — the reference marker(s) are the BLASTN query and the user's mitogenomes are the database; never cut the marker out of NCBI genomes and treat the user's sequences as the reference.

## Handoff

> Marker extraction complete. `mito_extract/marker.fasta` written (`<N>`/`<M>` taxa extracted). Point `preflight/phylo-preflight` at this file as `input_fasta` — its own validation (sequence count, duplicate/empty headers, nt/aa consistency, outgroup match) still runs normally on top of this.

---
name: phylo-taxon-sampling
description: 'Optional, opt-in pre-preflight stage for phylogenetics-agent: broaden a seed FASTA with additional same-marker sequences from NCBI (same genus/family/etc., primary GenBank submissions only — RefSeq records excluded) and an outgroup, with name-quality filtering, sequence-quality ranking, >=99.9% redundancy collapse, and a per-taxon cap. Writes an expanded FASTA plus a per-taxon summary CSV and a per-accession metadata CSV (with GPS coordinates where available). Triggers: "add more taxa", "pull sequences from NCBI", "add an outgroup", "broaden this to the genus/family", "phylo-taxon-sampling".'
version: 1.1.0
updated: "2026-09-08"
triggers:
  - "add more taxa"
  - "pull sequences from NCBI"
  - "add an outgroup"
  - "broaden this to the genus/family"
  - "phylo-taxon-sampling"
---

# phylo-taxon-sampling

> **v1.1.0.** Optional taxon-sampling stage for `phylogenetics-agent`. Runs *before* `preflight/phylo-preflight`, not instead of it — its output (an expanded FASTA) is handed to the normal preflight, which still runs its own header/sequence-type checks. Only invoke this when the user wants sequences beyond what they already have (genus/family broadening, an outgroup) — a user with a complete, self-sufficient FASTA skips this entirely.
>
> **Primary-submission-only (v1.1.0):** RefSeq records (`NC_`/`NG_`-style accessions) are **excluded**, not preferred. The esearch query carries `NOT srcdb_refseq[PROP]` and a post-fetch guard drops any straggler, logging it in `metadata.csv` with `drop_reason=refseq_excluded`. When a primary submission and its byte-identical RefSeq mirror both exist, the **primary accession is the one kept**. Type material still outranks ordinary primary submissions in the quality ranking.

## When to Use This Skill

Use when the user has a seed FASTA (or just a species/marker in mind) and wants it broadened with:
- other species of the same genus/family/etc., and/or
- one or two outgroup taxa for rooting.

Do NOT use if the user's FASTA is already complete for their analysis — this stage exists to *fill gaps*, not to replace user-curated input.

## 0. Inputs / Outputs contract

### Inputs (consumed)

| Path | Source | Required? |
| --- | --- | --- |
| `expand_taxon` (taxon name to search within, e.g. `"Escherichia"` or `"Enterobacteriaceae"`) | User | yes |
| `marker` (e.g. `"16S ribosomal RNA"`) | User | yes |
| `outgroup_taxon` (explicit name) or auto-pick flag | User | optional |
| `n_per_taxon`, redundancy/quality thresholds | User | optional (sane defaults) |

### Outputs (produced)

| Path | Owner | Format | Notes |
| --- | --- | --- | --- |
| `$RUN_DIR/taxon_sampling/expanded.fasta` | this skill | FASTA | Hand off to `preflight/phylo-preflight` as the input FASTA |
| `$RUN_DIR/taxon_sampling/summary.csv` | this skill | CSV | Per-taxon rollup: N kept, best-quality flag, GPS coverage, N dropped |
| `$RUN_DIR/taxon_sampling/metadata.csv` | this skill | CSV | Per-accession: full metadata incl. `lat_lon`, `kept`, `drop_reason` — traceable even for dropped candidates |

## 0.5 Ask-User Stop Points

### SP1 — No taxon-quality candidates found

| Trigger | Evidence | Action |
| --- | --- | --- |
| `Fetched: 0 candidate records` after the NCBI query | Query too narrow, marker name doesn't match NCBI title conventions, or taxon genuinely has no records for this marker | Ask: "No records found for `<marker>` in `<taxon>`. Pick: (A) broaden `expand_taxon` (e.g. genus -> family), (B) try an alternate marker name/synonym, (C) proceed without expansion" |

**Auto-pick when**: ≥ 1 candidate found. No ask.

### SP2 — Auto-picked outgroup needs confirmation

| Trigger | Evidence | Action |
| --- | --- | --- |
| `--outgroup-auto` was used (no explicit `--outgroup-taxon`) | The auto-pick is a single taxonomy-parent step up from `expand_taxon`, excluded via NOT — a heuristic approximation of a sister clade, not an authoritative phylogenetic outgroup choice | Ask: "Auto-picked outgroup candidate: `<taxon>`. Pick: (A) accept, (B) I'll give the correct outgroup taxon, (C) skip the outgroup" |

**Auto-pick when**: user supplied an explicit `--outgroup-taxon`. No ask.

### SP3 — Retrieval query too broad (large result count, slow/rate-limited)

| Trigger | Evidence | Action |
| --- | --- | --- |
| `esearch`'s `<Count>` in its XML response is in the thousands for a genus/family-level query | A genus-wide `efetch` over many thousand hits is slow and often rate-limited by NCBI without an API key — confirmed during testing: an unrestricted genus-level query took multiple minutes and was cancelled, while a species-restricted query with `-stop N` returned in seconds | Ask: "NCBI reports `<count>` hits for `<taxon>`/`<marker>` — that's a lot. Pick: (A) narrow to species level first then broaden later, (B) proceed with a small `--retmax` cap (default 200) and accept it's a sample not exhaustive, (C) get an NCBI API key to raise the rate limit" |

**Auto-pick when**: count is in the low hundreds or fewer. No ask — just proceed with `--retmax`.

## Procedure

### 1. Run the retrieval script

```bash
cd /path/to/phylogenetics-agent
python3 preflight/phylo-taxon-sampling/scripts/taxon_sampling.py \
  --expand-taxon "Escherichia" \
  --marker "16S ribosomal RNA" \
  --n-per-taxon 3 \
  --retmax 200 \
  --outgroup-taxon "Salmonella enterica" \
  -o "$RUN_DIR/taxon_sampling/expanded.fasta" \
  --summary-out "$RUN_DIR/taxon_sampling/summary.csv" \
  --metadata-out "$RUN_DIR/taxon_sampling/metadata.csv" \
  --esearch-cmd "pixi run --manifest-path pixi.toml esearch" \
  --efetch-cmd "pixi run --manifest-path pixi.toml efetch" \
  --vsearch-cmd "pixi run --manifest-path pixi.toml vsearch"
```

For auto-outgroup instead of an explicit `--outgroup-taxon`, pass `--outgroup-auto` (triggers SP2).

If the user already has a seed FASTA of their own sequences, concatenate it with `expanded.fasta` before handing off to preflight — this script only fetches the *additional* sequences, it does not merge in the user's existing file itself.

### 2. Selection criteria (what the script does)

1. **Name-quality filter**: drops `cf.` forms, unresolved `sp./spp.`, hybrids, and `uncultured`/`environmental sample`/`metagenome` entries — same spirit as `trim_list.py`'s organism-name filtering, adapted for phylogenetic (not biogeographic) use.
2. **Sequence-quality ranking** (best first, within each taxon): (a) NCBI type-material flag (RefSeq is excluded upstream — primary-submission-only since v1.1.0), (b) fewest ambiguous (`N`/IUPAC) bases, (c) length closest to the taxon's median candidate length, (d) submission recency as a tie-break.
3. **Redundancy collapse**: `vsearch --cluster_fast --id 0.999` within each taxon's candidate pool — sequences ≥99.9% identical are collapsed to the single highest-ranked representative; the rest are recorded in `metadata.csv` as `duplicate_of_<accession>`, not silently discarded.
4. **Per-taxon cap**: `n_per_taxon` (default 3) representatives kept per taxon, best-ranked first — mirrors `trim_list.py`'s two-pass `select_representatives` (exhaust the high-signal pool, then backfill).
5. **Outgroup**: explicit taxon name (fetched directly, same quality ranking, no cap) or `--outgroup-auto` (one NCBI-taxonomy-parent step up from `expand_taxon`, excluding it — an approximate sister clade, always confirmed at SP2).

### 3. Hand off to preflight

`expanded.fasta` becomes the input to `preflight/phylo-preflight`, which still runs its own full validation (≥4 sequences, dup/empty headers, nt/aa consistency, outgroup-in-headers check). This stage does not replace that gate.

## Interpretation Guidelines

- **GO**: ≥1 candidate retrieved per requested taxon, output FASTA has ≥1 new sequence.
- **GO-WITH-WARNINGS**: some taxa returned 0 candidates (noted per-row in `summary.csv`), or the outgroup was auto-picked (SP2) and needs user confirmation before the run proceeds.
- **NO-GO**: zero candidates for every taxon queried and the user declines to broaden/retry (SP1).

## Troubleshooting — Signature library

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `ERROR: Missing -db argument` from `efetch` | `esearch`'s XML wasn't piped into `efetch` (e.g. ran `efetch` standalone, or a broken pipe) | Confirm `esearch ... \| efetch ...` are chained, not run separately with `efetch` reading nothing on stdin. |
| `esearch: Unrecognized option -retmax` | This EDirect version has no `-retmax` flag on `esearch` | Cap results via `efetch -start 1 -stop N` instead (what the script does) — not an `esearch` flag. |
| Command hangs for minutes on a genus/family-level query | Broad taxon query returns thousands of hits; NCBI is slow/rate-limited without an API key | Narrow `expand_taxon` first (species-level), or accept a small `--retmax`; see SP3. |
| All candidates for a taxon show `sequence: ''` / kept 0 sequences despite `Fetched: N` | GenBank record's `ORIGIN` block wasn't parsed (e.g. a record format variant) | Check `docs-corpus/entrez-direct/cli-reference.md` for `-format` options; re-inspect a raw `efetch -format gb` capture for that accession directly. |
| Everything in a taxon's pool collapses into one cluster unexpectedly | `vsearch --cluster_fast --id 0.999` computes identity over the aligned overlap, so several short fragments of the same conserved gene region can appear ≥99.9% identical even at different total lengths — this is expected for well-conserved markers like 16S, not a bug | Lower `--redundancy-threshold` only if this is unwanted; otherwise it's correctly collapsing true near-duplicates. |
| `KeyError` on a dict field when editing this script | `parse_gb_record`'s returned dict must include every field `priority_key`/CSV writers reference — a local variable computed in the function but not added to the return dict silently breaks callers only when that code path runs | Diff the return dict against every `rec["..."]` access in the file before committing a change here. |

## Verification

- [ ] `$RUN_DIR/taxon_sampling/expanded.fasta` exists and has ≥1 sequence.
- [ ] `summary.csv` and `metadata.csv` both exist; `metadata.csv` row count ≥ `summary.csv`'s total N kept (dropped candidates are retained for traceability).
- [ ] Every kept row in `metadata.csv` has a non-empty `accession`/`organism`; `lat_lon` is `NA` where genuinely absent, not blank/missing.
- [ ] No kept row has `is_refseq=True` (primary-submission-only rule).

## Handoff

> Taxon sampling complete. `<N>` sequences added across `<N_taxa>` taxa (+ outgroup if requested). Next: invoke `preflight/phylo-preflight` on `$RUN_DIR/taxon_sampling/expanded.fasta` (merged with any seed FASTA the user already had) — it runs the full input-validation gate before any alignment work starts.

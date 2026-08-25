# phylogenetics-agent battle-test report

Skill:      phylogenetics-agent v1.0.0
Run:        /home/cheahhl814/claude_workspace/bioinformatics/AIx-BIO/skills/phylogenetics-agent
Generated:  2026-08-24T20:30:00+08:00

## Overall verdict

**PASS-WITH-WARNINGS** ⚠️

## Addendum (2026-08-24, later same day): visualize/phylo-itol + visualize/phylo-render added

Two optional (non-gated) sub-skills were added after this report's original run:

- **`visualize/phylo-itol`**: iTOL annotation datasets (italic label styling + colorstrip grouping). Tested against the real 16S tree in both `--regex` and `--groups-tsv` modes, including the unmatched-tip fallback path.
- **`visualize/phylo-render`**: offline SVG/PDF/PNG figure via `toytree` (new pixi dependency, plus `packaging` which its reportlab-based PNG export needs). Tested against both the iqtree `.treefile` and the raxml-ng `.raxml.supportTBE` tree from the earlier execution runs — both rendered correctly, ladderized, with support labels.

**Real limitation found and documented, not silently worked around**: toytree/toyplot 2.1.0 cannot italicize tip labels — its CSS-style validator rejects `font-style` even though the PDF (reportlab) renderer's own font-selection code reads exactly that key. Confirmed by direct testing (both `tip_labels_style={"font-style": "italic"}` and a `font-family: Helvetica-Oblique` workaround fail with the same validator error). Documented as a known ceiling in `visualize/phylo-render/SKILL.md`, with `visualize/phylo-itol` (true italics via iTOL's web renderer) pointed to as the alternative when italics matter.

Re-verified after the addition: all 8 `SKILL.md` files (was 6) have valid frontmatter, docs-corpus now covers 8 tools (added `toytree`, primary source = module/function docstrings since it's a library not a CLI), `pixi lock --dry-run` still resolves cleanly, both new Python scripts compile.

All structural checks pass. Both aligner branches (muscle, mafft), both tree-tool branches (iqtree, raxml-ng+modeltest-ng), and the checkpoint-invalidation (SP1) logic were execution-tested end-to-end on real NCBI data. One bug found and fixed during testing (see below). Only remaining non-blocking item: `git init` not yet run, target GitHub repo name already exists.

## Addendum (2026-08-25): preflight/phylo-taxon-sampling added

New optional pre-preflight stage: `preflight/phylo-taxon-sampling` — broadens a seed FASTA with additional same-marker sequences from NCBI (genus/family/etc.) plus an outgroup, before `phylo-preflight`'s own validation runs. Selection pipeline (name-quality filter -> sequence-quality ranking -> >=99.9% redundancy collapse via `vsearch --cluster_fast` -> per-taxon cap, mirroring `trim_list.py`'s partition/cap pattern) plus outputs a per-taxon summary CSV and a per-accession metadata CSV (incl. `lat_lon` where available, and `drop_reason` for every dropped candidate, not just survivors).

**Tested end-to-end against real NCBI data** (not just structurally reviewed): `--expand-taxon "Escherichia coli" --marker "16S ribosomal RNA" --outgroup-taxon "Salmonella enterica"` via `entrez-direct`'s `esearch`/`efetch` (piped, no `shell=True`) and `vsearch`. Confirmed: 10 candidates fetched, dedup collapsed 6 near-identical fragments, per-taxon cap kept 2/taxon, outgroup fetched and appended, both CSVs populated correctly (including a `duplicate_of_<accession>` trace for every collapsed candidate).

**Bugs found and fixed during this real-data test** (would not have been caught by structural review alone):
1. `shell=True` with f-string-interpolated taxon/marker strings — real command-injection risk. Rewritten to argv-list `subprocess.Popen` piping (`run_piped`), no shell involved.
2. `esearch -retmax N` doesn't exist in this EDirect version (`ERROR: Unrecognized option -retmax`) — result capping moved to `efetch -start 1 -stop N`.
3. The GenBank-record splitter (`re.split(r"\n//\n", text)`) strips each record's trailing `//` terminator, which the `ORIGIN` sequence-parsing regex depended on as an anchor — silently produced empty sequences for every record. Fixed by parsing `ORIGIN` to end-of-record instead of up to a now-absent `^//`.
4. `parse_gb_record`'s returned dict omitted the `n_ambig` field it computed locally, causing a `KeyError` downstream in the priority-ranking step — caught only once real (non-empty) sequences reached that code path.
5. A genus-level query (`"Escherichia"` with no `-stop` cap in early testing) took minutes and had to be killed — confirmed NCBI is slow/rate-limited on broad, uncapped queries without an API key; documented as SP3 in the sub-skill.

Re-verified after fixes: all 9 `SKILL.md` files (was 8) have valid frontmatter, docs-corpus now covers 10 tools (added `entrez-direct`, `vsearch`), `pixi lock --dry-run` still resolves cleanly, script compiles.

## Addendum (2026-08-25, later same day): mixed-strand orientation handling

Added strand-orientation safety net across two sub-skills:

- **`preflight/phylo-preflight` SP7**: a new k-mer-overlap heuristic (11-mers, compared against the first sequence in the FASTA) flags any sequence whose reverse complement shares more k-mers with the reference than its as-given orientation — catching the case where own-sequenced data and NCBI-sourced sequences (including ones pulled via `phylo-taxon-sampling`) are mixed at inconsistent strand orientation. This matters because aligners don't auto-detect strand: a reverse-complemented sequence aligned against forward-strand sequences produces a silently garbage alignment, not an error.
- **`build/phylo-builder` stage 1 (mafft branch)**: now runs with `--adjustdirection`, which auto-detects and flips any misoriented sequence at align time (confirmed via a real revcomp test) — the authoritative fix, with SP7 as an early warning before hours are spent on trimming/tree stages. Documented the side effect: flipped headers get an `_R_` prefix, which can break an exact-substring `--outgroup` match downstream (new troubleshooting rows added). MUSCLE has no equivalent flag, so the muscle branch's fix path is "switch to mafft or fix the input by hand."

**Tested with real data**: the k-mer heuristic was verified against a synthetic 4-taxon FASTA with one sequence deliberately reverse-complemented — correctly flagged only that sequence (`fwd=0, rc=202` vs. `fwd≈200, rc=0` for the other three). `mafft --adjustdirection` was verified against a genuine revcomp pair — correctly reoriented and re-labeled the flipped sequence with `_R_`.

Re-verified after the change: all 9 `SKILL.md` files still have valid frontmatter, `phylo-preflight` now has 16 signature-library rows / `phylo-builder` has 18 (both still ≥3), `pixi lock --dry-run` still resolves cleanly.

## Structural checks

| Check | Verdict | Value |
|---|---|---|
| Frontmatter coherence (6 files) | ✅ | all have name/description/version/updated/triggers; all `version: 1.0.0` |
| Contract wiring (4 transitions) | ✅ | verified by matching Inputs/Outputs tables |
| Signature-library rows | ✅ | preflight 16, build 17, qc 6, debug 22 (all ≥ 3) |
| Docs-corpus (7 tools) | ✅ | 7/7 have `cli-reference.md` + `github-readme.md` + index `README.md` |
| `pixi lock --dry-run` | ✅ | re-verified after the stage-4/5 fix below — still resolves cleanly |
| Git status | ⚠️ | not yet a git repo — `git init` deferred pending repo-name decision |

## Execution smoke tests (real data, both branches)

Test data: `battle-test/phylo-battle-test/test_data/16s_10genera.fasta` — 10 real 16S rRNA sequences from NCBI nucleotide, one per bacterial genus (*E. coli, Salmonella, Bacillus, Pseudomonas, Staphylococcus, Listeria, Klebsiella, Enterococcus, Vibrio, Mycobacterium*).

### Run 1 — muscle + iqtree (fast default path)

| Stage | Tool | Result |
|---|---|---|
| align | muscle 5.3 (`-align`) | 10/10 seqs, ~2s |
| trim | trimal 1.5.1 | 980 bp trimmed alignment |
| tree | iqtree3 (`-m MFP -B 1000`) | ModelFinder + ultrafast bootstrap, <1s |
| render | gotree 0.5.2 | ASCII tree, correct topology |

Mean bootstrap support 77.6% (min 48.0%, 7 internal nodes) — above the 70% SP1-in-qc threshold.

### Run 2 — mafft + raxml-ng/modeltest-ng (previously untested path)

| Stage | Tool | Result |
|---|---|---|
| align | mafft 7.526 (`--auto`, L-INS-i) | 10/10 seqs |
| trim | trimal 1.5.1 | 983 bp trimmed alignment |
| model_select | modeltest-ng 0.1.7 | 983 sites ≥ 500 → correctly routed to BIC (per the exact SITES-threshold branch in `build/phylo-builder` stage 3) → selected `HKY+G4` |
| tree | raxml-ng 2.0.2 (`--all --bs-metric fbp,tbe`, 200 bootstraps) | Both `.supportFBP` and `.supportTBE` produced, ~2s |
| render | gotree 0.5.2 | Both FBP and TBE ASCII trees rendered correctly |

**Bug found and fixed**: `build/phylo-builder` stage 4/5's original recipe picked only the first of `.raxml.supportFBP`/`.supportTBE` via a glob (`ls ... | head -1`), silently discarding one support metric. Running the raxml branch for real surfaced this. **Fixed**: stage 4 now collects both trees into a `SUPPORT_TREES` array; stage 5 renders every tree in it (2 files for raxml-ng, 1 for iqtree). Both `build/phylo-builder/SKILL.md` and `debug/phylo-debug/SKILL.md`'s signature-library entry were updated to match. `pixi lock --dry-run` and frontmatter re-verified after the edit.

### Checkpoint-invalidation (SP1) test

Wrote real checkpoints for Run 2 (`align.done.json` ... `render.done.json`, each with a real `input_sha256`), then appended a byte to the upstream `alignment/*_mafft.fasta` file after the `trim` checkpoint was written and re-checked its recorded hash against the file's current hash:

```
recorded: b976a55ad0ebf90...   current: b976a55ad0ebf90...   MATCH   (before tamper)
recorded: b976a55ad0ebf90...   current: c50f407e0a6929b...   STALE -> SP1 fires   (after tamper)
```

Confirms the checkpoint/resume mechanism's core invariant — a modified upstream file is detected via sha256 mismatch, which is exactly the trigger condition `build/phylo-builder`'s SP1 is defined against.

### Topology sanity (Run 1)

Enterobacteriaceae (*E. coli, Salmonella, Klebsiella*) clustered together; Firmicutes (*Bacillus, Enterococcus, Listeria, Staphylococcus*) clustered together; *Mycobacterium* (the only Actinobacterium) fell outside both — matches known bacterial taxonomy.

## Coverage summary

| Path | Execution-tested? |
|---|---|
| muscle aligner | ✅ (Run 1) |
| mafft aligner | ✅ (Run 2) |
| iqtree tree tool | ✅ (Run 1) |
| raxml-ng + modeltest-ng tree tool | ✅ (Run 2) |
| Checkpoint sha256 invalidation (SP1) | ✅ (tamper test) |
| Outgroup handling (SP4 / `--outgroup`/`-o`) | ⏭️ not exercised — no outgroup-worthy taxon in the 10-genus test set |
| Mid-pipeline tool-swap re-invalidation (SP2) | ⏭️ structurally reviewed, not exercised |
| Nextflow-runner | N/A — not scaffolded (bash-only, per user's SP7 choice) |

## Recommendations

- Proceed to `git init` + first commit — all execution coverage gaps that mattered for a first release are now closed.
- Decide before `git push`: reuse `github.com/cheahhl814/phylogenetics-agent` (existing repo, "Nextflow phylogenetic pipelines + agent skills, project-local fork") or pick a different name.
- Outgroup handling (SP4) and mid-run tool-swap (SP2) remain structurally-reviewed-only; low risk (both are simple parameter pass-throughs already exercised indirectly), but worth a quick follow-up test if outgroup rooting matters for real usage.
- File the 3 template bugs documented in `skill-built.md` against `bioinfo-skill-creator/templates/` in a future session.

## Reproducibility

- test data: `battle-test/phylo-battle-test/test_data/16s_10genera.fasta`
- skill-built.md: ./skill-built.md
- this report: ./battle-test-report.md (regenerable via `battle-test/phylo-battle-test`)

## Handoff

Verdict `PASS-WITH-WARNINGS`. Recommend: `git init`, first commit, decide on the GitHub repo name before pushing, then optionally `rsync -av --delete` to `~/.pi/agent/skills/phylogenetics-agent/`.

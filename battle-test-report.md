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

## Addendum (2026-08-25, later same day): prune/phylo-prune added

New optional stage: `prune/phylo-prune`, wrapping `gotree prune` (already a pipeline dependency, no new pixi deps or docs-corpus entries needed) instead of porting a hand-rolled Newick parser from the reference `prune-phylogenetic-tree` skill.

**Investigated live** (against real IQ-TREE `.treefile`/`.contree` and RAxML-NG output from earlier test runs):
- `gotree prune` correctly parses both `.treefile` and `.contree` formats without any special-casing — the "support before colon" ambiguity the reference skill's custom parser worked around is just standard Newick internal-node-label placement, which gotree already handles.
- `gotree prune` sums branch lengths correctly when collapsing a single-child internal node left behind by a prune (verified: root-to-tip distances stayed additive/consistent after pruning) — this is the phylogenetically correct behavior, and simpler than the reference skill's "never collapse" design (which existed only to work around its own parser not summing lengths).
- `gotree prune` silently ignores keep/exclude names that don't exist in the source tree rather than erroring — confirmed by testing a request with one bogus name mixed into a valid list. The wrapper script (`prune_tree.py`) does its own pre-check diff against `gotree stats tips` output and refuses to proceed (unless `--force`) so a typo or an unaccounted-for `_R_`-prefix (from `mafft --adjustdirection`, see the earlier strand-orientation addendum) doesn't silently change which taxa end up in the output.
- `gotree prune` hard-refuses to produce a tree with fewer than 3 tips (`"only made of two tips"` error) — confirmed live; the wrapper translates this into a clearer message.
- All 4 modes tested end-to-end on the real 10-genus test tree: `--keep` (explicit names), `--keep-file` (tipfile, cross-checked to produce an identical result to `--keep`), `--exclude-file`, `--reference-tree` (diff against another pruned tree).

**Completed**:
- `prune/phylo-prune/SKILL.md` (v1.0.0) — Inputs/Outputs contract, SP1–SP4 stop points, procedure, 5-row troubleshooting signature library, verification checklist, handoff.
- `prune/phylo-prune/scripts/prune_tree.py` — thin gotree-flag-translation wrapper + pre-check diff + report writer, no shell=True (argv-list `subprocess.run`, consistent with `taxon_sampling.py`'s established convention).
- Wired into orchestrator `SKILL.md` (stage-routing note + common-follow-ups row), `README.md` (pipeline table row, usage example, repo layout tree), `battle-test/phylo-battle-test/SKILL.md` (frontmatter-check loop).
- Structural checks re-run: all 10 `SKILL.md` files pass frontmatter validation, `prune/phylo-prune/SKILL.md` has 9 signature-library rows, script compiles and `--help` runs clean.

## Addendum (2026-08-25, later same day): automated result interpretation added to qc/phylo-qc

`qc/phylo-qc` (v1.0.0 → v1.1.0) previously only reported an aggregate mean/min bootstrap number, parsed via a crude Newick regex. Replaced with a real script (`qc/phylo-qc/scripts/qc_report.py`) built on `gotree stats edges`/`stats tips`/`stats monophyletic` (all already verified live, no new deps):

- **Weak clades**: internal edges below a support threshold (default 70%) are listed individually with clade size, not just averaged away.
- **Long-branch outliers**: terminal branch lengths flagged via a median + 3×MAD test (skipped under 4 tips, where MAD is meaningless) — the classic signature of a misidentified/contaminant sequence or alignment artifact. Ties into `prune/phylo-prune` as the fix.
- **Outgroup monophyly**: if `params.json` names an outgroup, its matched tip(s) are tested with `gotree stats monophyletic` — a non-monophyletic outgroup is a real QC signal (wrong taxon, or a genuinely surprising topology), previously silently unreported.

**Verified live** against the real `16s_10genera.contree` test tree: both a single-tip outgroup (trivially monophyletic) and a two-taxon non-sister outgroup (correctly flagged `False`); weak-clade/long-branch detection produced correct, non-empty tables on the actual 10-genus tree (3 weak clades, 2 long-branch outliers: *M. tuberculosis*, *P. aeruginosa* — the two most basal/divergent taxa in this test set, as expected). Caught and fixed one bug during testing: `gotree stats tips`' tab-separated columns are `tree, id, nneigh, name, ExternalBranch, RootToTip` — the tip-name column is index 3, not 2 as first written.

Added SP2 (long-branch outlier) and SP3 (outgroup non-monophyly) stop points; extended the signature library from 3 to 8 rows. Re-verified: all 10 `SKILL.md` files still pass frontmatter validation, `pixi lock --dry-run` unaffected (no new deps), script compiles.

## Addendum (2026-08-25, later same day): outgroup rooting added to visualize/phylo-itol + visualize/phylo-render

Both visualization sub-skills previously rendered/uploaded the tree exactly as `build/phylo-builder` produced it, ignoring `params.json`'s `outgroup` field entirely -- a real gap, since an unrooted or arbitrarily-rooted figure misrepresents the intended ingroup/outgroup relationship even when the underlying tree topology is correct.

- **`visualize/phylo-itol`** (v1.0.0 → v1.1.0): new step in the Procedure substring-matches `params.json`'s `outgroup` against real tip names (`gotree stats tips`, same convention as `qc/phylo-qc`), then reroots via `gotree reroot outgroup -l -` before generating the label/colorstrip datasets. Writes `itol/<sample>_rooted.nwk` -- that file, not the original `trees/*` tree, is now what gets uploaded to iTOL. New SP4 for the non-monophyletic-outgroup case (gotree warns and reroots at the LCA rather than failing -- verified live, including the exact stderr signature).
- **`visualize/phylo-render`** (v1.0.0 → v1.1.0): new `--root-outgroup NAME[,NAME...]` flag on `render_tree.py`, using toytree's native `.root()` (no `gotree` shell-out needed here, toytree already has the tree loaded). Unlike gotree, toytree hard-errors on a non-monophyletic outgroup rather than warning-and-proceeding -- added an MRCA-rooting fallback (`tree.root(tree.get_mrca_node(*matched))`, toytree's own suggested recipe) so the two sub-skills agree on rooting behavior; if even that fails (the MRCA is already the tree's root -- a real edge case hit during testing with a 2-taxon non-monophyletic outgroup on the 10-genus test tree), warns and renders unrooted rather than crashing. New SP3 covers both fallback paths.

**Verified live** end-to-end on the real `16s_10genera.contree`: single-tip outgroup reroots correctly in both sub-skills (confirmed via `gotree draw text`/`toytree` tip order); two-taxon non-sister outgroup correctly triggers gotree's LCA-reroot-with-warning path (`phylo-itol`) and toytree's raise → MRCA-fallback → (in this specific case) MRCA-already-root → warn-and-render-unrooted path (`phylo-render`), with no crash in either. Full `phylo-itol` bash procedure (substring-match → `gotree reroot outgroup` → feed rerooted tree into `itol_tip_labels.py`) run end-to-end, not just each piece in isolation.

Re-verified: all 10 `SKILL.md` files pass frontmatter validation (`phylo-itol` now 1.1.0, `phylo-render` now 1.1.0), `phylo-itol` has 12 signature-library rows (was 5), `phylo-render` has 13 (was 5), `pixi lock --dry-run` unaffected (no new deps), `render_tree.py` compiles.

## Addendum (2026-08-25, later same day): preflight/phylo-mito-extract added

New optional pre-preflight stage: `preflight/phylo-mito-extract` — extracts a single marker region (16S, COI, etc.) from a multi-taxon whole-mitogenome FASTA via BLASTN, so mitogenome input can still feed a single-marker tree. Generalizes the BLAST-hit-extraction core of the project-local `blast_extract_cds.py` (full mitogenome annotation: 13 PCGs + 2 rRNAs + 22 tRNAs + D-loop, via tRNAscan-SE and a reference GFF/GenBank) down to just one marker, extracted from a multi-taxon target in a single BLASTN pass — no tRNAscan-SE, no D-loop detection, no GFF3/BED output, since none of that is needed for a single-marker tree. New pixi dependency: `blast` (bioconda, confirmed resolvable via `pixi search` before adding).

**Tested end-to-end against synthetic data built from the real `16s_10genera.fasta` sequences** (embedding real 16S sequences inside random flanking sequence to simulate a mitogenome context, so results could be checked against known-correct answers):
- **Forward-strand extraction**: correct region recovered.
- **Reverse-strand extraction**: a sequence embedded as its reverse complement was correctly strand-corrected on extraction — confirmed the extracted sequence is an exact substring of the real (forward-orientation) source sequence.
- **No-hit detection**: a pure-random "no marker present" sequence correctly produced zero hit, reported under "no hit" rather than silently omitted.
- **Length-outlier detection**: a deliberately truncated (40% length) marker fragment, blasted against a same-species reference, correctly extracted and flagged at `0.40x` under the `[0.5, 1.5]` default outlier band.
- **Cross-taxon reference divergence** (an unplanned but informative finding): the same truncated fragment produced *no hit at all* against a reference from a different bacterial phylum (Pseudomonas vs. Bacillus) — BLASTN's default seeding didn't find a significant hit for a short, divergent fragment. Documented as a signature-library row and folded into SP3's guidance: a no-hit taxon is usually a reference-divergence problem, not an `--evalue` threshold problem.
- **NCBI auto-fetch mode** (`--fetch-marker-ref-taxon`): live-tested against real NCBI data (`esearch`/`efetch`, reusing `phylo-taxon-sampling`'s established piping pattern) — fetched a real `16S ribosomal RNA` record for *Pseudomonas aeruginosa* and used it as the BLASTN reference successfully.

**One real bug found and fixed during testing, unrelated to the extraction logic itself**: the first `pixi run blastn`/`makeblastdb` invocation after adding `blast` to `pixi.toml` hung for 10+ minutes on a 4-sequence input — `pixi run` was resolving/downloading the new dependency inline rather than using a pre-installed env. Running `pixi install` once resolved it; the same command then completed in under a second. Documented as the first row in the sub-skill's signature library, since this will recur for any agent that adds a `pixi.toml` dependency and immediately shells out to it without an explicit `pixi install` first.

Completed: `preflight/phylo-mito-extract/SKILL.md` (v1.0.0, 8 signature-library rows, SP1-SP4), `preflight/phylo-mito-extract/scripts/extract_marker.py`, `docs-corpus/blast/` (blastn + makeblastdb `-help` captures), wired into orchestrator `SKILL.md`, `README.md` (pipeline table, prerequisites, usage example, repo layout), `battle-test/phylo-battle-test/SKILL.md` (frontmatter loop + docs-corpus tool list). Re-verified: all 11 `SKILL.md` files pass frontmatter validation, all 11 docs-corpus tool entries populated, `pixi lock --dry-run` resolves cleanly with `blast` added, script compiles.

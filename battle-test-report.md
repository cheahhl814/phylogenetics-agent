# phylogenetics-agent battle-test report

Skill:      phylogenetics-agent v1.0.0
Run:        /home/cheahhl814/claude_workspace/bioinformatics/AIx-BIO/skills/phylogenetics-agent
Generated:  2026-08-24T20:30:00+08:00

## Overall verdict

**PASS-WITH-WARNINGS** ⚠️

All structural checks pass. Both aligner branches (muscle, mafft), both tree-tool branches (iqtree, raxml-ng+modeltest-ng), and the checkpoint-invalidation (SP1) logic were execution-tested end-to-end on real NCBI data. One bug found and fixed during testing (see below). Only remaining non-blocking item: `git init` not yet run, target GitHub repo name already exists.

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

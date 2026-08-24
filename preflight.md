# Skill creator preflight report

Run:        /home/cheahhl814/claude_workspace/bioinformatics/AIx-BIO/skills/phylogenetics-agent
Generated:  2026-08-24T19:45:00+08:00
Meta-skill: bioinfo-skill-creator v1.0.0

## Overall verdict

**GO-WITH-WARNINGS** ⚠️

Skill `phylogenetics-agent` queued for build with 7 tools (bash-only, checkpointed), inspired by `MLTree-main`. One warning: the target GitHub repo name already exists.

## Evidence

| Check | Verdict | Value | Threshold |
|---|---|---|---|
| Skill name (kebab-case) | ✅ | `phylogenetics-agent` | valid regex |
| Skill name uniqueness (local `@skills/`) | ✅ | no collision (dir was empty pre-scaffold) | unique |
| Target directory writable | ✅ | `$RUN_DIR` | writable |
| Tool inventory | ✅ | 7 tools (muscle, mafft, trimal, modeltest-ng, raxml-ng, iqtree, gotree) | ≥ 1 |
| Pixi env | ✅ | pixi 0.70.1 | installed |
| Tool availability (`pixi search`) | ✅ | 7/7 found in conda-forge/bioconda | all tools resolve |
| Git status | ⚠️ | NOT initialized | will `git init` at build |
| Disk space | ✅ | 147 GB free | ≥ 5 GB |
| GitHub repo | ⚠️ | `cheahhl814/phylogenetics-agent` **already exists** ("Nextflow phylogenetic pipelines (mitogenome + ML tree) + agent skills. Project-local fork.") | expected to not exist yet |

## Recommendations

- **Skill name**: `phylogenetics-agent` (user-provided; valid)
- **Skill shape**: `multi-tool-pipeline` (7 tools, clearly a multi-stage pipeline — auto-picked, not ambiguous despite SP3's >5 threshold, since the user explicitly named MLTree as the source pipeline)
- **Sub-skills**: preflight, run, qc, debug, battle-test (5-sub-skill template)
- **Nextflow runner**: `no` (user chose bash-only at SP7 — the point of this skill is to be *more* flexible than MLTree's rigid Nextflow DAG, with agent-driven checkpoints replacing the DAG)
- **Target tiers**: `large` only (SP9 auto-picked; no small-model mention)
- **Checkpoint design**: one `$RUN_DIR/checkpoints/<stage>.done.json` per stage (`align`, `trim`, `model_select`, `tree`, `render`) — the `run` sub-skill resumes from the latest completed checkpoint instead of re-running from scratch, and lets the user swap `align` (muscle/mafft) or `tree` (raxml-ng/iqtree) methods per-run without touching the other stages
- **pixi task names**: `preflight`, `run`, `qc`, `report`

## Tools

| Tool | Role | `pixi search` status |
|---|---|---|
| muscle | aligner (default) | ✅ found |
| mafft | aligner (alternative) | ✅ found |
| trimal | alignment trimming | ✅ found |
| modeltest-ng | substitution model selection (raxml branch) | ✅ found |
| raxml-ng | tree inference (default) | ✅ found |
| iqtree | tree inference (alternative) | ✅ found |
| gotree | ASCII tree rendering | ✅ found |

## Source pipeline reference

`/home/cheahhl814/claude_workspace/bioinformatics/PHYLOGENETIC/MLTree-main` (Nextflow DSL2, single monolithic `main.nf`, 7 processes, no preflight, no checkpointing, no ability to resume a partial run). The new skill keeps the same tool choices and stage order but replaces the single Nextflow workflow block with: a `preflight` sub-skill (FASTA validity, sequence count -> `large_dataset` auto-flag, duplicate/empty-header checks), a `run` sub-skill that executes each stage as a separate pixi-wrapped bash step and writes a checkpoint after each, a `qc` sub-skill that summarizes tree stats (taxa count, mean bootstrap support, alignment length before/after trimming), and `debug`/`battle-test` per the standard convention.

## Handoff

Verdict is `GO-WITH-WARNINGS` → hand off to `build/skill-builder`.

**Before first push**, confirm with the user whether to reuse the existing `github.com/cheahhl814/phylogenetics-agent` repo or pick a different name — this does not block local scaffolding.

## Reproducibility

- params.json: $RUN_DIR/params.json
- evidence:   $RUN_DIR/preflight_evidence.txt
- this report: $RUN_DIR/preflight.md (regenerable via this skill)

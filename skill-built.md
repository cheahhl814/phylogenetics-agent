# Skill build report

Skill:        phylogenetics-agent
Run:          /home/cheahhl814/claude_workspace/bioinformatics/AIx-BIO/skills/phylogenetics-agent
Generated:    2026-08-24T20:10:00+08:00
Meta-skill:   bioinfo-skill-creator v1.0.0

## Build summary

| Phase                      | Status | Notes                                                                                                                                                                                                                                                          |
| -------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Templates rendered         | ✅      | `SKILL.md` + `README.md` + `pixi.toml` rendered from Jinja2 templates (ORCHESTRATOR_SKILL.md.j2, README.md.j2, pixi.toml.j2), then hand-fixed for a template whitespace bug (see below) and a channel-selection bug in pixi.toml.j2                            |
| Sub-skills authored        | ✅      | 5 sub-skill `SKILL.md` files (preflight, build, qc, debug, battle-test) hand-authored with real MLTree-derived procedures — the generic `SUB_SKILL_SKILL.md.j2` template's Procedure section is a placeholder skeleton, not usable verbatim for domain content |
| Docs-corpus populated      | ✅      | 7/7 tools; 7/7 with `cli-reference.md` (primary, captured from the pinned pixi-resolved version's `--help`/`-h`), 7/7 with `github-readme.md` (secondary, via docs-ingest GitHub-repo strategy)                                                                |
| Nextflow-runner scaffolded | ⏭️     | skipped — user chose bash-only at preflight SP7                                                                                                                                                                                                                |
| Lite tree scaffolded       | ⏭️     | skipped — `target_tiers: ["large"]` only                                                                                                                                                                                                                       |
| `git init`                 | ⏭️     | not yet run — pending user confirmation (see warning below)                                                                                                                                                                                                    |
| `pixi lock --dry-run`      | ✅      | all 7 tools + transitive deps resolve on `linux-64`                                                                                                                                                                                                            |
| `pixi install`             | ✅      | ran during docs-corpus capture; env installed under `.pixi/`                                                                                                                                                                                                   |

## Template bugs found and worked around (not fixed upstream in bioinfo-skill-creator)

1. **`pixi.toml.j2` channel condition**: `tool_inventory[0].role in ['aligner', 'assembler', 'screener', 'validator']` only matches an *exact* role string. This skill's `params.json` uses `"aligner (default)"` (descriptive), so the condition never matched and `bioconda` was silently dropped from `channels`. Worked around by hand-writing `pixi.toml` directly (channels, `platforms = ["linux-64"]` since bioconda's raxml-ng/modeltest-ng/iqtree builds are Linux-only, and real task descriptions instead of the `echo` placeholders).
2. **Jinja whitespace**: rendering with `trim_blocks=True` collapsed the `{%- for %}` loops' manual newline control in `ORCHESTRATOR_SKILL.md.j2`, corrupting the YAML frontmatter (triggers list became one unparseable line). Fixed by re-rendering with default `Environment()` settings (no `trim_blocks`).
3. **Literal `<phase>` placeholders**: `ORCHESTRATOR_SKILL.md.j2` and `README.md.j2` hardcode the literal string `<phase>` in sub-skill path references (e.g. `preflight/<phase>-preflight`) rather than a Jinja variable — these are not auto-filled by any `params.json` field. Fixed via `sed` substitution to the real sub-skill names (`phylo-preflight`, `phylo-builder`, `phylo-qc`, `phylo-debug`, `phylo-battle-test`).

*(Recommend filing these three as fixes in `bioinfo-skill-creator/templates/` for the next skill build — not done in this session since the user's request was to build phylogenetics-agent, not patch the meta-skill.)*

## File inventory

| Path                                                                                                          | Size     | sha256 (first 16 hex)           |
| ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------- |
| SKILL.md                                                                                                      | 7384 B   | 665d9a957cce5ce1                |
| README.md                                                                                                     | 4501 B   | 304b5178ea757f84                |
| pixi.toml                                                                                                     | 1339 B   | eaeb59a6c3c0407f                |
| preflight/phylo-preflight/SKILL.md                                                                            | 9501 B   | b70ff1e055ae1077                |
| build/phylo-builder/SKILL.md                                                                                  | 11978 B  | 5a68de4859e1931d                |
| qc/phylo-qc/SKILL.md                                                                                          | 6077 B   | b004bc7f3625da7f                |
| debug/phylo-debug/SKILL.md                                                                                    | 7212 B   | d75b3a09ed3f1c00                |
| battle-test/phylo-battle-test/SKILL.md                                                                        | 5080 B   | d7e527b5689c20ac                |
| docs-corpus/{muscle,mafft,trimal,modeltest-ng,raxml-ng,iqtree,gotree}/{cli-reference,github-readme,README}.md | 21 files | see `docs-corpus/.fingerprints` |

## Reproducibility

- params.json: ./params.json
- preflight.md: ./preflight.md
- this report: ./skill-built.md (regenerable via this skill)

## Outstanding item

`github.com/cheahhl814/phylogenetics-agent` already exists (flagged at preflight). Confirm reuse vs. rename before `git push`.

## Handoff

Build succeeded. Next: invoke `battle-test/phylo-battle-test` to run the structural smoke tests.

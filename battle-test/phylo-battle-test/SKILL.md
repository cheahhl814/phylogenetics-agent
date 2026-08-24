---
name: phylo-battle-test
description: 'Structural quality gate for phylogenetics-agent: frontmatter coherence across all SKILL.md files, sub-skill contract wiring, signature-library completeness, docs-corpus population for all 7 tools, pixi.toml resolution, and (opt-in) an execution smoke test on a tiny synthetic FASTA. Writes battle-test-report.md. Triggers: "battle-test phylogenetics-agent", "phylo-battle-test", "is the tree skill ready".'
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "battle-test phylogenetics-agent"
  - "phylo-battle-test"
  - "is the tree skill ready"
---

# phylo-battle-test

> **v1.0.0.** Quality gate for `phylogenetics-agent`. Mirrors `bettamt-qc`'s structural-check pattern. Never modifies the skill — read-only checks plus one opt-in execution smoke test.

## 0. Inputs / Outputs contract

### Inputs

| Path | Required? |
| --- | --- |
| `$RUN_DIR/skill-built.md` | yes (refuses to run without it) |
| `$RUN_DIR/SKILL.md`, all sub-skill `SKILL.md` | yes |
| `$RUN_DIR/pixi.toml`, `$RUN_DIR/docs-corpus/` | yes |

### Outputs

| Path | Format |
| --- | --- |
| `$RUN_DIR/battle-test-report.md` | Markdown, verdict `PASS`/`PASS-WITH-WARNINGS`/`FAIL` |

## Procedure

### 1. Frontmatter coherence

```bash
for f in SKILL.md preflight/phylo-preflight/SKILL.md build/phylo-builder/SKILL.md \
         qc/phylo-qc/SKILL.md debug/phylo-debug/SKILL.md battle-test/phylo-battle-test/SKILL.md \
         visualize/phylo-itol/SKILL.md visualize/phylo-render/SKILL.md; do
    python3 -c "
import yaml
fm = open('$f').read().split('---')[1]
d = yaml.safe_load(fm)
assert all(k in d for k in ('name','description','version','updated','triggers')), 'missing key in $f'
print('$f OK:', d['name'], d['version'])
"
done
```

Master and all sub-skills should share `version: 1.0.0` (first release — will diverge after individual updates, which is expected).

### 2. Contract wiring

- `preflight/phylo-preflight` outputs `params.json` + `preflight.md` → `build/phylo-builder` inputs list the same two paths. ✅ (verified by reading both files' §0 tables)
- `build/phylo-builder` outputs `checkpoints/render.done.json` → `qc/phylo-qc` inputs list it. ✅
- `qc/phylo-qc` outputs `qc-report.md` → orchestrator's stage-detection ladder checks for it (`qc-done` stage). ✅

### 3. Signature-library completeness

```bash
for f in preflight/phylo-preflight/SKILL.md build/phylo-builder/SKILL.md \
         qc/phylo-qc/SKILL.md debug/phylo-debug/SKILL.md; do
    N=$(grep -c '^| `' "$f")
    [ "$N" -ge 3 ] && echo "$f: $N signature rows OK" || echo "$f: only $N rows — FAIL"
done
```

### 4. Docs-corpus freshness

```bash
for tool in muscle mafft trimal modeltest-ng raxml-ng iqtree gotree toytree; do
    d="docs-corpus/$tool"
    [ -f "$d/README.md" ] || { echo "$tool: MISSING README.md — FAIL"; continue; }
    if [ -f "$d/cli-reference.md" ] || [ -f "$d/github-readme.md" ] || [ -f "$d/web-docs.md" ]; then
        echo "$tool: OK ($(ls "$d" | tr '\n' ' '))"
    else
        echo "$tool: index exists but zero content sources — FAIL"
    fi
done
```

### 5. Pixi parse

```bash
pixi lock --dry-run --manifest-path pixi.toml
```

### 6. Git hygiene

```bash
git -C . status --porcelain | grep -q . && echo "uncommitted changes present" || echo "clean"
```

### 7. (Opt-in, `--execution`) Tiny synthetic-FASTA smoke test

Only run when explicitly requested (real tool execution, several minutes even on a 4-sequence input due to modeltest-ng + bootstrap).

```bash
cat > /tmp/phylo_smoke.fasta <<'EOF'
>taxon_A
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
>taxon_B
ACGTACGTACGTACGTACGTACGTACGTTCGTACGTACGT
>taxon_C
ACGAACGTACGAACGTACGTACGTACGTACGTACGAACGT
>taxon_D
ACGTACGAACGTACGTACGAACGTACGTACGTACGTACGT
EOF
# Run preflight + build/phylo-builder with tree_tool=iqtree (skips the modeltest-ng stage, faster)
# and bootstrap_replicates=100 (fast) against this file. Verify all 5 checkpoints + qc-report.md.
```

## Interpretation Guidelines

- **PASS**: all structural checks pass, `pixi lock --dry-run` succeeds, every tool has ≥ 1 docs-corpus source, at most 1 `WARN`.
- **PASS-WITH-WARNINGS**: 1 non-blocking issue (e.g. uncommitted `git status`, one tool with only a `web-docs.md` source).
- **FAIL**: any missing docs-corpus entry, broken contract wiring, `pixi lock` failure, or a sub-skill with < 3 signature-library rows.

## Verification

- [ ] All 6 `SKILL.md` files have valid frontmatter.
- [ ] Contract wiring verified for all 4 phase transitions.
- [ ] All 4 phase sub-skills (preflight, build, qc, debug) have ≥ 3 signature-library rows.
- [ ] All 7 tools have a populated `docs-corpus/<tool>/`.
- [ ] `pixi lock --dry-run` succeeds.
- [ ] `git status` reported (clean or not — informational, not blocking unless the user asked for a clean commit).

## Handoff

> Battle-test complete. Verdict: `<verdict>`. If `PASS`/`PASS-WITH-WARNINGS`, recommend `git init` + first commit + `git push` to `github.com/cheahhl814/phylogenetics-agent` (note: this repo name already exists — confirm reuse vs. rename before pushing) and deploy via `rsync -av --delete` to `~/.pi/agent/skills/phylogenetics-agent/`.

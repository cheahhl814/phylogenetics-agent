---
name: phylo-battle-test
description: 'Structural quality gate for phylogenetics-agent: frontmatter coherence via skill-forge''s skill-lint.py, sub-skill contract wiring, signature-library completeness, docs-corpus freshness, pixi lock, git/artifact hygiene, self-update wiring, README hygiene, and (opt-in) a synthetic-FASTA execution smoke test. Writes battle-test-report.md. Triggers: "battle-test phylogenetics-agent", "phylo-battle-test", "is the tree skill ready".'
version: 1.1.0
updated: "2026-11-16"
triggers:
  - "battle-test phylogenetics-agent"
  - "phylo-battle-test"
  - "is the tree skill ready"
disable-model-invocation: true
---

# phylo-battle-test

> Quality gate for `phylogenetics-agent`. Read-only checks plus one opt-in execution smoke test. When skill-forge's `bin/skill-lint.py` is available, it is the source of truth for frontmatter / git hygiene / update-check wiring / README hygiene — if the bash snippets here and the linter disagree, fix the linter, not this file.

## 0. Inputs / Outputs contract

### Inputs

| Path | Required? |
| --- | --- |
| `$RUN_DIR/SKILL.md`, all sub-skill `SKILL.md` | yes |
| `$RUN_DIR/pixi.toml`, `$RUN_DIR/docs-corpus/`, `$RUN_DIR/params.json` | yes |
| `$RUN_DIR/skill-built.md` | no — gitignored by design; expected absent in the shipped repo. Its absence is informational, not a failure. |

### Outputs

| Path | Format |
| --- | --- |
| `$RUN_DIR/battle-test-report.md` | Markdown, verdict `PASS`/`PASS-WITH-WARNINGS`/`FAIL` |

## Procedure

### 1. Frontmatter coherence (via skill-lint.py when available)

```bash
# Preferred: skill-forge's structural linter (frontmatter contract, C1/C6/C9/C11/C12/C14/C15)
python3 <skill-forge>/bin/skill-lint.py "$RUN_DIR"

# Fallback: manual check of every SKILL.md
for f in $(find "$RUN_DIR" -name "SKILL.md" -not -path "*/.git/*"); do
    python3 -c "
import yaml
d = yaml.safe_load(open('$f').read().split('---')[1])
assert all(k in d for k in ('name','description','version','updated','triggers')), 'missing key in $f'
print('$f OK:', d['name'], d['version'])
"
done
```

Master and sub-skill versions are **not** expected to match — sub-skills version independently after release. Only the frontmatter contract is enforced.

### 2. Contract wiring

- `preflight/phylo-preflight` outputs `params.json` + `preflight.md` → `build/phylo-builder` inputs list the same two paths.
- `build/phylo-builder` outputs `checkpoints/*.done.json` (terminal: `render.done.json`) → `qc/phylo-qc` inputs list it.
- `qc/phylo-qc` outputs `qc-report.md` → orchestrator's stage-detection ladder checks for it (`qc-done` stage).
- Optional chains: `phylo-taxon-sampling` / `phylo-mito-extract` outputs feed the same preflight gate; `phylo-prune` consumes the QC-approved tree; `phylo-itol` / `phylo-render` render it.

Verify by reading the Inputs/Outputs tables in each sub-skill's `SKILL.md` — do not infer from prose.

### 3. Signature-library completeness

```bash
for f in $(find "$RUN_DIR" -path '*/phylo-*/SKILL.md' -not -path "*/.git/*"); do
    N=$(grep -cE '^\| `' "$f")
    [ "$N" -ge 3 ] && echo "$f: $N signature rows OK" || echo "$f: only $N rows — WARN"
done
```

Sub-skills that legitimately deal with failures (preflight, builder, qc, debug, taxon-sampling, mito-extract, prune, itol, render) should carry ≥3 signature rows each. The orchestrator `SKILL.md` itself is exempt (it delegates, it does not execute).

### 4. Docs-corpus freshness

```bash
for tool in $(jq -r '.tool_inventory[].name' "$RUN_DIR/params.json"); do
    d="docs-corpus/$tool"
    [ -f "$d/README.md" ] || { echo "$tool: MISSING README.md — FAIL"; continue; }
    srcs=$(ls "$d"/cli-reference.md "$d"/github-readme.md "$d"/web-docs.md 2>/dev/null | wc -l)
    [ "$srcs" -ge 1 ] && echo "$tool: OK ($srcs source(s))" || echo "$tool: zero populated sources — FAIL"
done
test -f docs-corpus/.fingerprints && echo ".fingerprints OK" || echo ".fingerprints MISSING — WARN"
```

### 5. Pixi parse

```bash
pixi lock --dry-run --manifest-path pixi.toml
```

### 6. Git hygiene

```bash
# .gitignore must cover the meta-skill run artifacts
for pat in docs-corpus/.fingerprints skill-built.md battle-test-report.md battle-test_evidence.txt preflight.md preflight_evidence.txt; do
    grep -q "$pat" .gitignore && echo "OK  $pat" || echo "MISSING  $pat"
done
# No run artifact may be tracked; params.json MUST stay tracked
git ls-files -c -- skill-built.md battle-test-report.md battle-test_evidence.txt preflight.md preflight_evidence.txt
# ↑ must print nothing
git ls-files -i -c --exclude-standard   # ↑ must print nothing (tracked-and-ignored trap)
git ls-files --error-unmatch params.json >/dev/null && echo "params.json tracked OK"
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

### 8. Self-update wiring

```bash
test -x bin/skill-update-check.py && echo "update-check executable OK" || echo "update-check missing/not executable — FAIL"
python3 -m py_compile bin/skill-update-check.py && echo "parses OK"
grep -q "update-check" pixi.toml && echo "pixi task OK" || echo "pixi task MISSING — FAIL"
grep -q "update-check" README.md  && echo "README documents it OK" || echo "README section MISSING — WARN"
# Informational (exit 0/1/2 all acceptable here):
python3 bin/skill-update-check.py || true
```

### 9. README hygiene

```bash
README=README.md
grep -nE '\[Describe|\{\{|\{%|preflight-artifact|scaffold-render|├── run/' "$README" && echo "placeholders/stale paths FOUND — FAIL" || echo "no placeholders OK"
grep -nE '/home/[a-z]|/Users/|~/.pi/agent/skills|AGENTS\.md' "$README" && echo "machine-path/agent-config leak — FAIL" || echo "no machine-path leaks OK"
for s in "## Contents" "## 🚀 Installation" "## 💡 Usage" "## 🔬 Pipeline overview" "## 🧰 Tools" "## 🔄 Update check" "## 📁 Repository layout" "## 🔒 Hard guarantees" "## Provenance"; do
    grep -qF "$s" "$README" && echo "OK: $s" || echo "MISSING: $s — FAIL"
done
```

### 10. Fixtures (opt-in) + execution canary

- `test-data/make_fixtures.py` present and deterministic (two runs → identical `MANIFEST.tsv`) → OK; absent → WARN (skill predates the fixtures convention; note it, do not fail).
- `evals/evals.json` + `evals/triggers.json` present and parse as JSON; TODO markers acceptable but must be reported.
- Execution canary is opt-in only and never feeds the verdict: record per-tool EXEC-PASS/SKIP/FAIL in a separate `exec-canary-report.md`; an EXEC-FAIL surfaces as a WARN note in the report at most.

## Interpretation Guidelines

- **PASS**: checks 1–6 and 8–9 pass, `pixi lock --dry-run` succeeds, every tool has ≥ 1 docs-corpus source, at most 1 WARN.
- **PASS-WITH-WARNINGS**: 1 non-blocking issue (e.g. git status dirty, one tool with a single source, missing fixtures, unfilled evals TODOs).
- **FAIL**: any missing/zero-source docs-corpus entry, broken contract wiring, `pixi lock` failure, a sub-skill with < 3 signature rows, or a README hygiene hard fail.

## Verification

- [ ] Checks 1–6 and 8–9 all run; results written to `$RUN_DIR/battle-test-report.md`.
- [ ] Verdict line follows the PASS / PASS-WITH-WARNINGS / FAIL rubric above.
- [ ] Opt-in sections (7, 10) run only when the user asked; their results are reported separately and never upgraded into the verdict.

## Handoff

> Battle-test complete. Verdict: `<verdict>`. If `PASS`/`PASS-WITH-WARNINGS`, the skill is structurally sound; push to `github.com/cheahhl814/phylogenetics-agent` and deploy with a one-way rsync `@skills/phylogenetics-agent/ → ~/.agents/skills/phylogenetics-agent/` (per AGENTS.md §4a), then `diff -rq` to verify zero drift.

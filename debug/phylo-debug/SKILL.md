---
name: phylo-debug
description: 'Interpret failures in the phylogenetics-agent pipeline (preflight, align/trim/model_select/tree/render stages, qc) by matching stderr against a signature library, and recommend a concrete fix. Writes debug-report.md with verdict RECOVERABLE or BLOCKED. Triggers: "debug the tree pipeline", "phylogenetics run failed", "phylo-debug", "raxml crashed", "iqtree error".'
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "debug the tree pipeline"
  - "phylogenetics run failed"
  - "phylo-debug"
  - "raxml crashed"
  - "iqtree error"
  - "muscle failed"
---

# phylo-debug

> **v1.0.0.** Failure-interpreter phase of `phylogenetics-agent`. Mirrors `bettamt-debug`: read the failing command's stderr, match against the signature library below, and either resolve directly or investigate further. Never retries blindly.

## 0. Inputs / Outputs contract

### Inputs

| Path | Source | Required? |
| --- | --- | --- |
| Failing stage name + stderr | User / `build/phylo-builder` | yes |
| `$RUN_DIR/params.json`, `preflight.md` | upstream | yes |

### Outputs

| Path | Format | Notes |
| --- | --- | --- |
| `$RUN_DIR/debug-report.md` | Markdown | Diagnosis + fix; verdict `RECOVERABLE` or `BLOCKED` |

## Procedure

1. Identify which stage failed (`align`/`trim`/`model_select`/`tree`/`render`) from the missing/absent checkpoint in `$RUN_DIR/checkpoints/`.
2. Read the actual stderr — do not guess from the stage name alone.
3. Match against the signature library below.
4. If no match: re-run the failing command with `--verbose`/`-v` if the tool supports it, and re-check the docs-corpus entry for that tool (`$RUN_DIR/../docs-corpus/<tool>/cli-reference.md` relative to this skill, i.e. `phylogenetics-agent/docs-corpus/<tool>/`) before concluding.
5. Write `debug-report.md`: failing stage, matched signature (or "no match — investigated manually"), diagnosis, concrete fix (command + tool/version), verdict.

## Signature library

### Preflight-stage failures

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `grep: <fasta>: No such file or directory` | Wrong input path | `ls -la` to verify. |
| `Sequence count: 0` | Not a FASTA file, or wrong line endings (CRLF) | `file <fasta>`; `dos2unix` if CRLF. |
| Duplicate headers not caught before alignment | Preflight SP2 was skipped or bypassed | Re-run preflight; do not proceed on `NO-GO`. |

### Align stage

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `muscle: command not found` | Not installed in the active pixi env | `pixi install`; verify with `pixi run muscle -version`. |
| `muscle ... Out of memory` on `-align` (not `-super5`) | Dataset larger than the `large_dataset` threshold auto-detected | Force `-super5`: set `large_dataset: true` in `params.json` and re-run stage 1. |
| `mafft: command not found` | Same as muscle | `pixi install`. |
| `mafft --auto` hangs on very large N | MAFFT's `--auto` picks a slow accurate mode for large N | Switch aligner to `muscle -super5`, or use `mafft --retree 1` manually (not exposed as a `params.json` field — power-user override). |

### Trim stage

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `trimal: command not found` | Not installed | `pixi install`. |
| Output `*_trimal.fasta` has 0 columns / trimAl exits with a warning about no columns kept | Alignment too divergent, or `-nogaps -terminalonly` too aggressive for this input | Inspect `*_trimal.html`; consider running trimAl with `-gappyout` instead (manual override) if terminal-gap-only trimming removes everything. |

### Model-select stage (raxml branch)

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `modeltest-ng: command not found` | Not installed | `pixi install`. |
| Empty model string after AICc/BIC parse (exact MLTree-main guarded failure) | `.out` format changed between modeltest-ng versions, or `--force` output was truncated | Open `modeltest/*.out` directly; look for `Best model according to AICc`/`BIC` blocks manually. Route to SP3 in `build/phylo-builder`. |
| `modeltest-ng ... -T raxml` errors "invalid partition" | FASTA has non-standard characters modeltest-ng doesn't accept | Check for gap-only columns or non-IUPAC characters left after trimming. |

### Tree stage

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `raxml-ng: command not found` | Not installed | `pixi install`. |
| `raxml-ng: ERROR: model is empty` | `$MODEL` was blank when stage 4 ran (model_select stage 3 didn't actually block) | Re-check `checkpoints/model_select.done.json`; if missing/stale, re-run stage 3 before stage 4. |
| `raxml-ng ... --outgroup ERROR: taxon <X> not found` | Outgroup name mismatch (should have been caught at preflight SP4) | Re-run preflight with the exact FASTA header text. |
| `raxml-ng` runs for a very long time with no output | `bootstrap_replicates` set very high (e.g. 10000) on a large alignment | This is expected — RAxML-NG bootstrapping is the most compute-heavy stage. Reduce `bootstrap_replicates` if this is dev iteration, not a final run. |
| `iqtree: command not found` | Not installed | `pixi install`. |
| `iqtree ... ERROR: No outgroup taxa found` | Same outgroup mismatch as raxml-ng | Same fix. |
| `iqtree` picks a model that seems wrong for the data | ModelFinder ran on the full (untrimmed) alignment by mistake | Verify stage 4 was given `$TRIMMED`, not the raw alignment — check the checkpoint's `input_file` field. |

### Render stage

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `gotree: command not found` | Not installed | `pixi install`. |
| `gotree draw text` output is empty or garbled | Wrong support-tree file passed to gotree, or a stale checkpoint from before v1.0.0's fix (which rendered only the first of FBP/TBE) | v1.0.0 renders both FBP and TBE trees for the raxml branch (`build/phylo-builder` stage 5) — re-run stage 5 if the checkpoint predates this fix. |
| `gotree` errors on a `.treefile` from iqtree | iqtree's Newick sometimes embeds support as node comments (`[&support=...]`) rather than plain labels | Strip `[&...]` comments before passing to gotree, or use `iqtree`'s own `.contree`/`.splits.nex` if present. |

### QC stage

| Signature | Likely cause | Fix |
| --- | --- | --- |
| `No support values parsed` | Newick support-label convention doesn't match the regex in `qc/phylo-qc` | Inspect the tree file directly; adjust the parse or read `.iqtree`'s NOTE section for the exact convention. |

## Interpretation Guidelines

- **RECOVERABLE**: signature matched, fix is a concrete command or a `params.json` field change. Agent can re-run `build/phylo-builder` (it will resume from the invalidated stage per its checkpoint logic — no need to re-run earlier stages).
- **BLOCKED**: no signature matched after manual investigation, or the fix requires the user's judgment (e.g. deciding the input data itself is unsuitable).

## Verification

- [ ] `$RUN_DIR/debug-report.md` exists with a verdict.
- [ ] The fix references a concrete command or `params.json` field, not a vague suggestion.

## Handoff

> Debug complete. Verdict: `<RECOVERABLE|BLOCKED>`. If `RECOVERABLE`, invoke `build/phylo-builder` again — it resumes from the invalidated stage automatically.

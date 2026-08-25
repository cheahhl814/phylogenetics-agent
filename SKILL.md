---
name: phylogenetics-agent
description: Agentic single-marker maximum-likelihood phylogenetic tree pipeline (align -> trim -> model-select -> tree -> render), inspired by the MLTree Nextflow pipeline, rebuilt as a checkpointed BettaMt-pattern skill with per-stage preflight, resumable checkpoints, and stage-swap flexibility (muscle/mafft aligner, raxml-ng/iqtree tree tool).
version: 1.0.0
updated: "2026-08-24"
triggers:
  - "phylogenetic tree"
  - "ML tree"
  - "maximum likelihood tree"
  - "raxml"
  - "iqtree"
  - "phylogenetics agent"
  - "build a tree from these sequences"
  - "MLTree"
---

# Phylogenetics Agent

> **v1.0.0.** Checkpointed, agent-driven single-marker ML phylogenetics pipeline (align, trim, model-select, tree, render) with swappable tools at each stage and per-stage resume.

## Audience

This skill serves two purposes:

- **AI Agents**: Triggered by the phrases above. The agent must follow the strict evidence chain and run the Go/No-Go gates.
- **Human Users**: Provides a transparent audit trail.

## When to Use This Skill

Use this skill when you need to:

- Build a maximum-likelihood phylogenetic tree from a multi-FASTA alignment of one marker (e.g. 16S, COI, a single-copy gene).
- Want to swap the aligner (MUSCLE/MAFFT) or tree tool (RAxML-NG/IQ-TREE) mid-project without re-running the whole pipeline from scratch.
- Need to resume a run that stopped partway (e.g. after alignment, before the bootstrap-heavy tree step) instead of re-running everything.

**Do NOT use this skill** if:

- Multi-marker / whole-genome phylogenomics with concatenation or coalescent methods (out of scope; this is single-marker only).
- You want the original rigid Nextflow DAG for HPC cohort batch runs with no agent involvement — use MLTree-main directly instead.

## 0. Orchestrator — detect stage, route to the right sub-skill

This meta-skill is a **router**, not a doer. It does not duplicate logic from the sub-skills. Its job is to ask: **"what stage is the user at, and which sub-skill should they invoke next?"**

### 0.1 Locate the run directory

By convention the agent writes handoff files (see §B) to a run directory. Default: the current working directory. Override with `RUN_DIR` env var.

### 0.2 Detect the user's stage

Try to detect automatically **before** asking:

```bash
# Stage detection ladder — first match wins
test -f "$RUN_DIR/qc-report.md" && STAGE="qc-done"
test -f "$RUN_DIR/checkpoints/render.done.json" && STAGE="qc"
test -f "$RUN_DIR/checkpoints/tree.done.json" && STAGE="run"
test -f "$RUN_DIR/checkpoints/model_select.done.json" && STAGE="run"
test -f "$RUN_DIR/checkpoints/trim.done.json" && STAGE="run"
test -f "$RUN_DIR/checkpoints/align.done.json" && STAGE="run"
test -f "$RUN_DIR/preflight.md" && STAGE="run"
: "${STAGE:=preflight}"
```

If auto-detection is ambiguous, ask the user one short question (see **SP0** in §0.5).

### 0.5 Master ask-user stop points

This orchestrator has **one** user-facing stop point (SP0). All other stop points live in the sub-skills. The pattern is **Evidence + Recommend + Options**.

#### SP0 — Entry-stage ambiguity

| Trigger | Ask |
|---|---|
| Stage detection returns `preflight` AND no upstream artifact exists | "I don't see the upstream artifact. Did you run the upstream skill?" |

**Auto-pick when**: upstream artifact exists OR user just said "run phylogenetics-agent" with no other context → default to `preflight` stage.

#### Routing rule

Auto-pick the default when the evidence is unambiguous. Ask only when the agent genuinely cannot decide.

### 0.3 Route to the right sub-skill

| Stage | Action |
| --- | --- |
| `preflight` | Invoke `preflight/phylo-preflight`. Validates inputs, writes `preflight.md` + `params.json`. |
| `run` | Invoke `build/phylo-builder`. Runs the main workflow. |
| `qc` | Invoke `qc/phylo-qc`. Builds the final report. |
| `qc-done` | Show the user `$RUN_DIR/qc-report.md`. Ask if they want `prune/phylo-prune`, `visualize/phylo-itol`, or `visualize/phylo-render` next (all optional — not Go/No-Go gated phases). |

**`preflight/phylo-taxon-sampling` is optional and user-triggered**, invoked *before* `preflight/phylo-preflight` when the user wants the FASTA broadened with more taxa (same genus/family/etc.) and/or an outgroup pulled from NCBI. Its output (`taxon_sampling/expanded.fasta`) becomes the input FASTA to the normal preflight gate — it does not bypass preflight's own validation. See `preflight/phylo-taxon-sampling/SKILL.md`.

**`preflight/phylo-mito-extract` is optional and user-triggered**, also invoked *before* `preflight/phylo-preflight`, when the input is whole mitogenome sequences but the tree should be built from a single marker (16S, COI, Cytb, etc.). BLASTNs a reference marker sequence against the multi-taxon mitogenome FASTA and extracts the best-hit region per taxon. Its output (`mito_extract/marker.fasta`) becomes the input FASTA to the normal preflight gate, same handoff pattern as `phylo-taxon-sampling`. See `preflight/phylo-mito-extract/SKILL.md`.

**Do not skip preflight.** The preflight sub-skill computes evidence and writes `params.json` that the run sub-skill consumes.

**`visualize/phylo-itol` and `visualize/phylo-render` are optional and user-triggered**, not part of the Preflight→Run→QC gate chain. Invoke either (or both — they don't conflict) after `qc-report.md` exists: `phylo-itol` for interactive iTOL annotation datasets (label styling / colorstrip grouping, true italics), `phylo-render` for an offline scriptable SVG/PDF/PNG figure (no italics — a real toyplot limitation, see its SKILL.md). See `visualize/phylo-itol/SKILL.md` and `visualize/phylo-render/SKILL.md`.

**`prune/phylo-prune` is optional and user-triggered**, also after `qc-report.md` exists. Trims the final tree down to a curated subset of taxa (keep list, exclude list, or diff against a reference pruned tree) via `gotree prune`. Run it before `visualize/phylo-itol`/`phylo-render` if the user wants the visualization built on the pruned tree instead of the full one. See `prune/phylo-prune/SKILL.md`.

### 0.4 The run command

This skill ships **bash recipes** for each phase. The pixi tasks are the entry point for single-machine runs.

```bash
# Run the preflight
pixi run preflight

# Run the main workflow (after preflight passes)
pixi run run

# Run the QC (after the main workflow finishes)
pixi run qc
```

## A. Pipeline Architecture

The analysis is divided into **three sequential phases**: Preflight → Run → QC. The agent MUST complete each phase in order and pass the associated "Go/No-Go" gate. **`Run` is itself checkpointed into 5 internal stages** (`align → trim → model_select → tree → render`) — see `build/phylo-builder/SKILL.md` for the resume logic. This is the flexibility MLTree-main lacked: a partial run can resume from the last completed stage, and the aligner (muscle/mafft) or tree tool (raxml-ng/iqtree) can be swapped without re-running upstream stages.

### Phase 1: Preflight (The Audit)

**Goal**: Validate inputs, compute evidence, and write `params.json` + `preflight.md`.

- **Sub-skill**: `preflight/phylo-preflight`
- **Must-Verify**: All tools present; input FASTA has ≥ 4 unique-header sequences of one marker.
- **Exit Gate**: `$RUN_DIR/preflight.md` exists with overall verdict ≥ `GO-WITH-WARNINGS`.

### Phase 2: Run (The Workflow)

**Goal**: Execute the main workflow.

- **Sub-skill**: `build/phylo-builder`
- **Must-Verify**: Preflight verdict ≥ `GO-WITH-WARNINGS`.
- **Exit Gate**: The expected artifact exists.

### Phase 3: QC (The Report)

**Goal**: Build the final report.

- **Sub-skill**: `qc/phylo-qc`
- **Must-Verify**: Run output present.
- **Exit Gate**: `$RUN_DIR/qc-report.md` exists with verdict.

## B. The Evidence Chain & Handoff Contract

| From → To | Artifact | Owner | Consumer |
| --- | --- | --- | --- |
| Upstream → Preflight | Input files | upstream | `preflight/phylo-preflight` |
| Preflight → Run | `preflight.md` + `params.json` | `preflight/phylo-preflight` | `build/phylo-builder` |
| Run → QC | Run artifact | `build/phylo-builder` | `qc/phylo-qc` |
| QC → User | `qc-report.md` | `qc/phylo-qc` | User |

## C. Output contract — no artifact

This orchestrator skill produces **no file of its own**. All artifacts are produced by the sub-skills.

## D. Go/No-Go Gates

The agent must stop and warn the user if:

- **Preflight `NO-GO`**: `preflight.md` shows `NO-GO` verdict.
- **QC `NO-GO`**: `qc-report.md` shows `NO-GO` verdict.

## E. Common follow-ups

| User says | What to do |
| --- | --- |
| "Show me my last report" | `cat $RUN_DIR/qc-report.md` |
| "What did the run produce?" | Read `$RUN_DIR/qc-report.md` |
| "Can I publish this?" | Point to `$RUN_DIR/preflight.md` + `$RUN_DIR/qc-report.md` as audit-trail artifacts. |
| "Visualize the tree" / "iTOL annotation" / "colorstrip" | Invoke `visualize/phylo-itol` — writes `itol/<sample>_labels.txt` (+ `_colorstrip.txt`, `_legend.md` if a grouping was given). Upload alongside the tree file at itol.embl.de. |
| "Render a publication figure" / "export tree as PDF/SVG/PNG" | Invoke `visualize/phylo-render` — writes `figures/<sample>.{svg,pdf,png}`. No italics (toyplot limitation) — use `phylo-itol` instead if italic species names are required. |
| "Add more taxa" / "pull sequences from NCBI" / "add an outgroup" | Invoke `preflight/phylo-taxon-sampling` *before* `preflight/phylo-preflight` — writes `taxon_sampling/expanded.fasta` + summary/metadata CSVs, then hand off to the normal preflight gate. |
| "Extract 16S/COI from these mitogenomes" / "my input is whole mitogenomes" | Invoke `preflight/phylo-mito-extract` *before* `preflight/phylo-preflight` — writes `mito_extract/marker.fasta` + a report, then hand off to the normal preflight gate. Ask for a reference marker sequence (or an NCBI taxon to auto-fetch one from) if not already clear from the request. |
| "Prune the tree" / "remove these taxa" / "drop misidentified sequences" | Invoke `prune/phylo-prune` — writes `pruned/<sample>_pruned.nwk` + a report. Ask which mode (keep list / exclude list / match a reference tree) if not already clear from the request. |

## Verification

- [ ] Preflight was performed; `preflight.md` overall verdict ≥ `GO-WITH-WARNINGS`.
- [ ] Run completed; expected artifact exists.
- [ ] QC was performed; `qc-report.md` exists with verdict.

## Handoff pointers

After this orchestrator routes the user to a phase, the agent should explicitly state which sub-skill was invoked and what file it produces.

## Provenance

Built with the [bioinfo-skill-creator](https://github.com/cheahhl814/bioinfo-skill-creator) meta-skill. Pattern adopted from [BettaMt-agents](https://github.com/cheahhl814/BettaMt-agents).
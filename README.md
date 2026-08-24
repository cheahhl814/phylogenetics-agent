# Phylogenetics Agent

> **v1.0.0.** Checkpointed, agent-driven single-marker ML phylogenetics pipeline (align, trim, model-select, tree, render) with swappable tools at each stage and per-stage resume.

This is the **phylogenetics-agent** skill, built with the [bioinfo-skill-creator](https://github.com/cheahhl814/bioinfo-skill-creator) meta-skill.

## Pipeline Overview

The analysis follows a strict **3-phase evidence chain**. Moving to a subsequent phase requires passing a "Go/No-Go" quality gate AND emitting the artifact the next phase expects.

| # | Phase | Goal | Sub-Skill | Artifact produced |
|:---|:---|:---|:---|:---|
| **1** | **Preflight** (The Audit) | Validate inputs, compute evidence, write `preflight.md` + `params.json`. | `/preflight` | `$RUN_DIR/preflight.md` + `$RUN_DIR/params.json` |
| **2** | **Run** (The Workflow) | Execute the main workflow. | `/build` | `$RUN_DIR/checkpoints/tree.done.json + trees/` |
| **3** | **QC** (The Report) | Build the final report. | `/qc` | `$RUN_DIR/qc-report.md` |
| *opt.* | **Visualize** (iTOL annotation) | Generate iTOL label-style + colorstrip datasets. Not gated — user-triggered after QC. | `visualize/phylo-itol` | `$RUN_DIR/itol/*.txt` |
| *opt.* | **Render** (static figure) | Offline SVG/PDF/PNG figure via toytree — no browser/upload. Not gated. | `visualize/phylo-render` | `$RUN_DIR/figures/*.{svg,pdf,png}` |

## When to Use This Skill

✅ **Use this skill** when you need to:

- Build a maximum-likelihood phylogenetic tree from a multi-FASTA alignment of one marker (e.g. 16S, COI, a single-copy gene).
- Want to swap the aligner (MUSCLE/MAFFT) or tree tool (RAxML-NG/IQ-TREE) mid-project without re-running the whole pipeline from scratch.
- Need to resume a run that stopped partway (e.g. after alignment, before the bootstrap-heavy tree step) instead of re-running everything.

❌ **Do NOT use this skill** for:

- Multi-marker / whole-genome phylogenomics with concatenation or coalescent methods (out of scope; this is single-marker only).
- You want the original rigid Nextflow DAG for HPC cohort batch runs with no agent involvement — use MLTree-main directly instead.

## Prerequisites

- A pixi environment with the required tools: `muscle, mafft, trimal, modeltest-ng, raxml-ng, iqtree, gotree, toytree`.
- A multi-FASTA file of unaligned, same-marker sequences (at least 4 taxa) with unique sequence headers.

## Installation

```bash
# Initialize a pixi workspace (run once)
pixi init phylogenetics-agent-env
cd phylogenetics-agent-env

# Add the required channels
pixi workspace channel add conda-forge

# Install all tools from the skill's pixi.toml
pixi add --manifest-path /path/to/phylogenetics-agent/pixi.toml
```

## Usage

The skill is normally driven by an AI agent that reads the master `SKILL.md`, detects the current stage from filesystem state, and routes to the right sub-skill. For manual invocation:

```bash
# Phase 1: Preflight
RUN_DIR=/path/to/run
pixi run preflight

# Phase 2: Run (after Phase 1 passes)
pixi run run

# Phase 3: QC (after Phase 2 finishes)
pixi run qc

# Inspect outputs
cat $RUN_DIR/qc-report.md

# Optional: iTOL annotation datasets (after QC, user-triggered, not gated)
python3 visualize/phylo-itol/scripts/itol_tip_labels.py "$TREE" -o "$RUN_DIR/itol/labels.txt" --gotree-cmd "pixi run gotree"
python3 visualize/phylo-itol/scripts/itol_colorstrip.py "$TREE" -o "$RUN_DIR/itol/colorstrip.txt" --regex '^([A-Za-z]+)_' --gotree-cmd "pixi run gotree"

# Optional: offline SVG/PDF/PNG figure (after QC, user-triggered, not gated)
python3 visualize/phylo-render/scripts/render_tree.py "$TREE" -o "$RUN_DIR/figures/tree"
```

Each phase has explicit **Inputs/Outputs contract** at the top of its sub-skill SKILL.md. If the upstream artifact is missing, the sub-skill **must refuse to proceed** and tell the user which upstream step to run.

## Repository Layout

```
phylogenetics-agent/
├── SKILL.md                            # Master orchestrator (router only)
├── README.md                           # This file
├── pixi.toml                           # Pixi env: muscle, mafft, trimal, modeltest-ng, raxml-ng, iqtree, gotree, toytree
├── preflight/
│   └── phylo-preflight/SKILL.md      # Phase 1 — input validation
├── build/
│   └── phylo-builder/SKILL.md        # Phase 2 — main workflow
├── qc/
│   └── phylo-qc/SKILL.md             # Phase 3 — final report
├── debug/
│   └── phylo-debug/SKILL.md          # Failure interpreter (signature library)
├── battle-test/
│   └── phylo-battle-test/SKILL.md    # Structural smoke tests
├── visualize/                           # Both optional, not gated, don't conflict
│   ├── phylo-itol/                   # Interactive iTOL annotation datasets
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── itol_tip_labels.py
│   │       └── itol_colorstrip.py
│   └── phylo-render/                 # Offline SVG/PDF/PNG figure (toytree)
│       ├── SKILL.md
│       └── scripts/
│           └── render_tree.py
├── docs-corpus/                         # Offline Markdown snapshot of upstream tool docs
│   └── muscle/
│       └── README.md
└── test_smoke.py                       # Skill-level structural smoke test
```

## Provenance

Built with the [bioinfo-skill-creator](https://github.com/cheahhl814/bioinfo-skill-creator) meta-skill. Pattern adopted from:

- **BettaMt-agents** — https://github.com/cheahhl814/BettaMt-agents
- **bacterial-genome-analysis** — https://github.com/cheahhl814/bacterial-genome-analysis
- **amr-gene-screening** — https://github.com/cheahhl814/amr-gene-screening

## License

Same as the rest of the AiX-BIO skill tree (private GitHub repo, MIT-style — see repository owner).
# Ge–Sb–Te–C with machine-learned potentials: a record of simulations

LAMMPS simulations of Ge₂Sb₂Te₅ + x% C with machine-learned (Allegro) potentials, kept as one record across
potentials and studies. Compositions: x = 0, 1, 2.5, 5 and 10 at.% C (actual 0, 1.07, 2.54, 5.14 and 9.96), starting
from rocksalt cells with C on cation-vacancy sites. x = 10 is deliberately the vacancy-free endpoint (every vacancy
filled), so it differs from the others in vacancy count as well as C content; see `structures/build_supercells.py`.

Every potential is registered in `models/provenance.md` under a `MODEL_ID` (`common/model.sh`); every study keeps its
settings, runs and results per `MODEL_ID`, so potentials never share a directory and can be compared study by study.
**`RUNBOOK.md`** is the order of steps for a new potential: register it, validate it, then run the studies.

**Three potentials are compared:** `nequip_no_zbl`, `nequip_zbl` and `rushik_zbl_pairwise`, trained from scratch on the
same PAW data with identical settings except the short-range term (none; ZBL for all pairs; per-pair ZBL at the edge
of the data). Each is compared with DFT and with the others. Their training configs, logs and checkpoints are in
`training/`.

## Potentials × studies

| Study | Directory | `nequip_no_zbl` (no ZBL; default) | `nequip_zbl` | `rushik_zbl_pairwise` |
|---|---|---|---|---|
| Validation | `tests/` | done: all gate and physics tests pass; vs DFT RMS 5.4 meV/atom on the model_check frames, 2 fs timestep; glass as dense as the crystal (`tests/results/nequip_no_zbl/RESULTS.md`) | compiling (2026-11-18) | compiling (2026-11-18) |
| Melt-quench | `meltquench/` | done: 15 glasses at 10 K/ps (4×4×4), x0 and x10 at 5 and 1 K/ps (1 K/ps partially crystallizes); density, Tm_app, Tg and structure against C; report and slides (`meltquench/results/nequip_no_zbl/`) | — | — |
| Recrystallization | `recryst/` | calibration done, criterion 3.9 Å/0.6/4 (`recryst/calib/nequip_no_zbl/`); ramps x0, x5, x10 done (Tx 583, 650 K; x10 none below 900 K); Phase A (x0, 500–700 K) done; Phase B x1/x2p5 partly done, the rest of Phase B cancelled 2026-11-18 (`RUNBOOK.md`, status) | — | — |
| Coexistence | `coexistence/` | planned | — | — |
| Phases | `phases/` | done: 8 DFT cells (amorphous, rocksalt, trigonal; 0–10% C) at 300 K vs DFT-MD; RDF and ADF close (R 0.05–0.08, ADF overlap 0.92–0.98), Ge/Sb/Te VDOS 0–9% soft, C VDOS overlap 0.61–0.72 (`phases/results/nequip_no_zbl/RESULTS.md`) | — | — |
| Cascades | `cascades/` | planned | — | — |

## Study layout
Each study directory has:
- `README.md`: the method (no model's numbers except as labelled examples);
- its LAMMPS inputs and submit scripts, which take everything model-specific from `common/model.sh` /
  `common/defaults.sh` (the potential, `DT`) and from `params/<MODEL_ID>.sh` (the study's design numbers, each with
  its source);
- `runs/<MODEL_ID>/`: raw run directories (not tracked; `*/runs/` in `.gitignore`). Each holds `lmp_inputs/<log>/`,
  written by `common/run_lmp.sh` when the run starts: a copy of the input and its includes, the exact command
  (`run_command.sh`) and the provenance (`run_info.txt`: git commit, model file and sha256, container, node, job), for
  human reference;
- `results/<MODEL_ID>/`: summaries and write-ups, starting with `RESULTS.md` (tracked).

To add a study, create the directory with this layout and a section in `RUNBOOK.md`; nothing else changes. To add a
potential, follow `RUNBOOK.md` A–B, then give each study a `params/<MODEL_ID>.sh`.

## Layout
- `structures/`: the cleaned single rocksalt cell of each composition, named by atom count (`x0_461.data`,
  `x1_466.data`, `x2p5_473.data`, `x5_486.data`, `x10_512.data`), the source of every supercell; `build_supercells.py`
  writes NxNxN cells to `NNN/` (not tracked; 4×4×4 for the melt-quench and recrystallization); the original ASE-written inputs are in `original/`. See `structures/README.md`.
- `training/`: the training and test data, and per potential (`configs/<MODEL_ID>/`) its config, training log and best
  checkpoint (`CKPT`). See `training/README.md`.
- `models/`: the model registry (`provenance.md`: every potential, its checkpoint and compiled files with hashes), the
  compiled files, one per node type and model (`<MODEL_ID>[.G|.N|.K].nequip.pt2`, not tracked), and `compile_model.sh`.
- `common/`:
  - `model.sh`: `MODEL_ID` (default `nequip_no_zbl`) and its checkpoint, sources, timestep `DT`, container and DFT data;
  - `defaults.sh`: the compiled model `MODEL` for this node;
  - `run_lmp.sh`: the container launcher, one MPI rank per GPU; it records each run's inputs (`record_inputs.sh`);
  - the shared LAMMPS includes `in.potential`, `in.analysis` and `in.rdf`.
- `tests/`: validation of a potential (model, timestep, throughput, physics against DFT), the logic tests of the study
  inputs (`mq_logic/`, `recryst_logic/`) and the analysis checks (`mq_analysis/`, `dft_glass/`). Each writes a
  `RESULT*.txt` in place; `tests/collect.sh --save <MODEL_ID>` copies them to `tests/results/<MODEL_ID>/`. Summaries:
  `tests/results/<MODEL_ID>/RESULTS.md` per potential; `tests/RESULTS.md` describes the test suite and the
  model-independent environment checks (container, node types).
- `meltquench/`, `recryst/`, `coexistence/`, `phases/`, `cascades/`: the studies (layout above). `recryst/calib/`
  holds the crystallinity calibration and `recryst/scripts/` the recrystallization workflow. `phases/structures/` and
  `phases/dft/` hold the DFT cells and the DFT RDF/ADF/VDOS they are compared with.
- `analysis/`: post-processing with `env/`:
  - melt-quench: `mq_summary.py`, `mq_structure.py`;
  - recrystallization: `recryst_summary.py`, `rate_compare.py`;
  - phases: `phases_compare.py` (RDF, ADF, VDOS vs DFT), `build_dospt.sh` (builds DoSPT into `env/dospt/`);
  - shared helpers: `runio.py` (run-output readers) and `bondorder.py` (Q4 crystallinity, matching
    `common/in.analysis`);
  - `latent_features.py` (exploratory, `tests/latent_feasibility/`) runs in the container.
- `env/`: the analysis-only conda environment (`environment.yml`) and the DoSPT build (`env/dospt/`, not tracked).
  Simulations run in the container.

## Requirements
This workflow runs on Purdue's **Gilbreth** cluster. It needs read access to **`/depot/prism`**, which holds:
- the LAMMPS + pair_allegro container;
- each potential's training folder (`TRAIN_DIR`, from which it is compiled), and for `rushik_zbl_pairwise` the modified
  nequip/allegro sources that compile and load it;
- the DFT training and test sets;
- the DFT-MD of the phase cells (`$DFT_PHASES`, read by `phases/dft/make_dft_refs.py`) and the DoSPT source that
  `analysis/build_dospt.sh` builds (needs `gfortran`).

All of these paths are in `common/model.sh`. Elsewhere, provide equivalents and set them there. Slurm accounts
`strachan` (A30), `perc` (A100-40GB) and/or `alta` (A100-80GB).

## Running
All jobs run through `common/run_lmp.sh NGPU -in ... -log ...`, with the compiled model chosen per node type by
`common/defaults.sh` (`MODEL`; see `models/provenance.md`). Usable GPUs:
- `a30` with account `strachan` (submit-script default; 6 A30s shared by the group);
- `a100-40gb` with account `perc` (10 A100s, about 1.8× faster per GPU): `sbatch -A perc -p a100-40gb ...`;
- `a100-80gb` with account `alta` (36 A100-80GBs): `sbatch -A alta -p a100-80gb --constraint=K ...`. Only the
  k-nodes have a compiled file (`.K`); the i-nodes have none.

Analysis environment (the package cache must be on scratch, because the home quota is small):
```
module load conda/2025.09
export CONDA_PKGS_DIRS=/scratch/gilbreth/$USER/.conda_pkgs
conda env create -p env/cgst-ana -f env/environment.yml     # once
conda activate ./env/cgst-ana
```

Report documents (`meltquench/results/nequip_no_zbl/report/`): the figures need `env/cgst-ana` (matplotlib, OVITO) and
the PDF needs `module load texlive/20220321`. The slide deck needs Node.js with `pptxgenjs`, which are not part of
`env/` or the cluster (`build_deck.js` header). `pip install --target <dir> nodejs-bin` into a scratch directory
provides node.

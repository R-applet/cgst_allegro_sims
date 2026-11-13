# Ge₂Sb₂Te₅ + x% C: melt-quench and recrystallization with Allegro in LAMMPS

Compositions: x = 0, 1, 2.5, 5 and 10 at.% C (actual 0, 1.07, 2.54, 5.14 and 9.96), starting from rocksalt cells with C on
cation-vacancy sites. x = 10 is deliberately the vacancy-free endpoint (every vacancy filled), so it differs from
the others in vacancy count as well as C content; see `structures/build_supercells.py`.

The workflow is model-independent. The potential is named by `MODEL_ID` in `common/model.sh`. Its design numbers are
in `<study>/params/<MODEL_ID>.sh`, and its runs and results live in `<MODEL_ID>/` subdirectories. **`RUNBOOK.md`** is the
order of steps for a new model, with what each step must show.

| Part | Directory | run5_ep301 (archived, tag `run5_ep301-final`) | Next model |
|---|---|---|---|
| 1. Environment, model, Slurm tests | `env/`, `models/`, `common/`, `tests/` | done (`tests/RESULTS.md`); glass as dense as the crystal, inherited from the DFT reference (1g, 1k) | retrained potential pending; `RUNBOOK.md` Part 0–1 |
| 2. Melt-quench | `meltquench/` | 15 glasses at 10 K/ps and x0, x10 at 1 K/ps (`meltquench/results/run5_ep301/`) | Part 2 |
| 3. Recrystallization | `recryst/` | criterion 3.8 Å/0.6/4; ramps; Phase A x0 at 600/650 K (`recryst/results/run5_ep301/RESULTS.md`) | Part 3 |

## Layout
- `structures/`: the original 512-site cells (untouched), `build_supercells.py`, and the cleaned single rocksalt cell
  of each composition, named by atom count: `x0_461.data`, `x1_466.data`, `x2p5_473.data`, `x5_486.data`,
  `x10_512.data` (written by `build_supercells.py --nrep 1`). The builder writes cleaned NxNxN cells to `111/`,
  `222/` and `333/` (production uses 333, 12.4k–13.8k atoms; these directories are not tracked). It also fixes
  the 0.5 Å boundary gap in gst/c1/c2_5 and the missing masses in gst/c10; see its docstring.
- `models/`: the compiled potentials, one file per node type and model (`<MODEL_ID>[.G|.N].nequip.pt2`, not tracked),
  their provenance and hashes (`provenance.md`), and `compile_model.sh`.
- `params/`: one file per model, `<MODEL_ID>.sh`, with every hand-set design number (melt temperature, ramp ceiling and
  rate, Ta guard, barostat, halt level, grid) and its source. It also sources the generated calibration,
  `recryst/calib/<MODEL_ID>/calib_params.sh`.
- `common/`:
  - `model.sh`: `MODEL_ID` and its checkpoint, sources, container and DFT data paths;
  - `defaults.sh`: the timestep `DT` and the compiled model `MODEL` for this node;
  - `run_lmp.sh`: the container launcher, one MPI rank per GPU;
  - the shared LAMMPS includes `in.potential`, `in.analysis` and `in.rdf`.
- `tests/`: Part 1 tests (run5_ep301's results in `tests/RESULTS.md`), the logic tests of the Part 2/3 inputs
  (`mq_logic/`, `recryst_logic/`) and the analysis checks (`mq_analysis/`, `dft_glass/`). Each writes a `RESULT.txt`;
  `tests/collect.sh` prints them all.
- `meltquench/`, `recryst/`: the Part 2 and Part 3 inputs, submit scripts and method READMEs. Runs go to
  `runs/<MODEL_ID>/` and results to `results/<MODEL_ID>/`. `recryst/calib/` holds the crystallinity calibration and
  `recryst/scripts/` the Part 3 workflow.
- `analysis/`: post-processing with `env/`:
  - Part 2: `mq_summary.py`, `mq_structure.py`;
  - Part 3: `recryst_summary.py`, `rate_compare.py`;
  - shared helpers: `runio.py` (run-output readers) and `bondorder.py` (Q4 crystallinity, matching
    `common/in.analysis`);
  - `latent_features.py` (exploratory, `tests/latent_feasibility/`) runs in the container.
- `env/`: the analysis-only conda environment (`environment.yml`). Simulations run in the container.

## Requirements
This workflow runs on Purdue's **Gilbreth** cluster. It needs read access to **`/depot/prism`**, which holds:
- the LAMMPS + pair_allegro container;
- the modified nequip/allegro sources that compile and load the checkpoints;
- the checkpoints and the DFT training and test sets.

All of these paths are in `common/model.sh`. Elsewhere, provide equivalents and set them there. Slurm accounts
`strachan` (A30) and/or `perc` (A100-40GB).

## Running
All jobs run through `common/run_lmp.sh NGPU -in ... -log ...`, with the compiled model chosen per node type by
`common/defaults.sh` (`MODEL`; see `models/provenance.md`). Usable GPUs:
- `a30` with account `strachan` (submit-script default; 6 A30s shared by the group);
- `a100-40gb` with account `perc` (10 A100s, about 1.8× faster per GPU): `sbatch -A perc -p a100-40gb ...`.

`a100-80gb` needs its own model build first.

Analysis environment (the package cache must be on scratch, because the home quota is small):
```
module load conda/2025.09
export CONDA_PKGS_DIRS=/scratch/gilbreth/$USER/.conda_pkgs
conda env create -p env/cgst-ana -f env/environment.yml     # once
conda activate ./env/cgst-ana
```

Report documents (`meltquench/results/run5_ep301/report/`): the figures need `env/cgst-ana` (matplotlib, OVITO) and
the PDF needs `module load texlive/20220321`. The slide deck needs Node.js with `pptxgenjs`, which are not part of
`env/` or the cluster (`build_deck.js` header). `pip install --target <dir> nodejs-bin` into a scratch directory
provides node.

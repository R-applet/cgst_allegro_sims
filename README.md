# Ge₂Sb₂Te₅ + x% C: melt-quench and recrystallization with Allegro (run5_ep301) in LAMMPS

Compositions: x = 0, 1, 2.5, 5 and 10 at.% C (actual 0, 1.07, 2.54, 5.14 and 9.96), starting from rocksalt cells with C on
cation-vacancy sites. x = 10 is deliberately the vacancy-free endpoint (every vacancy filled), so it differs from
the others in vacancy count as well as C content; see `structures/build_supercells.py`.

| Part | Directory | Status |
|---|---|---|
| 1. Environment, model, Slurm tests | `env/`, `models/`, `common/`, `tests/` | done (`tests/RESULTS.md`); glass as dense as the crystal, inherited from the DFT reference (1g, 1k) |
| 2. Melt-quench | `meltquench/` | production runs done: 15 glasses at 10 K/ps (5 compositions × 3) and x0, x10 at 1 K/ps, all past the MSD gate; results not yet written up |
| 3. Recrystallization (Tx ramp, isothermal anneal) | `recryst/` | criterion calibrated (3.8 Å, 0.6, 4); 1 K/ps and 0.2 K/ps ramps running; results in `recryst/RESULTS.md` |

## Layout
- `structures/`: the original 512-site cells (untouched) and `build_supercells.py`. The builder writes cleaned NxNxN cells to
  `111/`, `222/` and `333/` (production uses 333, 12.4k–13.8k atoms). It also fixes the 0.5 Å boundary gap in
  gst/c1/c2_5 and the missing masses in gst/c10; see its docstring.
- `models/`: the compiled potential, its provenance and hashes, and a recompile script.
- `common/`: shared LAMMPS includes (`in.potential`, `in.analysis`, `in.rdf`), `run_lmp.sh` (container launcher,
  one MPI rank per GPU) and `defaults.sh` (production timestep `DT` and per-node compiled model `MODEL`; sourced
  by the Part 2/3 submit scripts and some tests; the Part 2/3 logic tests take only `MODEL`).
- `tests/`: Part 1 tests (results in `tests/RESULTS.md`), the logic tests of the Part 2/3 inputs (`mq_logic/`,
  `recryst_logic/`) and the melt-quench analysis checks (`mq_analysis/`, `dft_glass/`), reported in
  `meltquench/README.md` and `recryst/README.md`. Each writes a `RESULT.txt`; `tests/collect.sh` prints them all.
- `meltquench/`, `recryst/`: the Part 2 and Part 3 inputs, submit scripts and READMEs (protocol, outputs, running).
  `recryst/scripts/` wraps the Part 3 steps after calibration; `recryst/RESULTS.md` records the Part 3 results.
- `analysis/`: post-processing with `env/`: `mq_summary.py` and `mq_structure.py` (Part 2), `recryst_summary.py`
  (Part 3), and the shared helpers `runio.py` (run-output readers) and `bondorder.py` (Q4 crystallinity, matching
  `common/in.analysis`). `latent_features.py` (exploratory, `tests/latent_feasibility/`) runs in the container.
- `env/`: the analysis-only conda environment (`environment.yml`). Simulations run in the container.

## Running
All jobs run through `common/run_lmp.sh NGPU -in ... -log ...`, with the compiled model chosen per node type by
`common/defaults.sh` (`MODEL`; see `models/provenance.md`). Usable GPUs:
- `a30` with account `strachan` (submit-script default; 6 A30s shared by the group);
- `a100-40gb` with account `perc` (10 A100s, about 1.8× faster per GPU): `sbatch -A perc -p a100-40gb ...`.

`a100-80gb` needs its own model build first.

Analysis environment (the package cache must be on scratch; the home quota is full):
```
module load conda/2025.09
export CONDA_PKGS_DIRS=/scratch/gilbreth/$USER/.conda_pkgs
conda env create -p env/cgst-ana -f env/environment.yml     # once
conda activate ./env/cgst-ana
```

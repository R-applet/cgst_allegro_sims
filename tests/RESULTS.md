# Test suite and environment

What each test in `tests/` checks, how it is run and what it must show, plus the facts about the cluster and the
container that do not depend on the potential. Each potential's results are in `tests/results/<MODEL_ID>/RESULTS.md`
(with the machine-written `RESULT*.txt` copies next to it); the order in which the tests gate the studies is
`RUNBOOK.md`, B. The labels (1a–1k) are the names the other documents use for the tests.

## Running
Each test directory has a batch script, run from inside that directory with `sbatch`: `submit.sh`, except
`scaling/submit_all.sh` and `scaling/submit_size.sh` (plain bash, submit the jobs themselves), `env_probe/probe.sh`,
and the CPU-only Python checks `dft_glass/check.py` and `mq_analysis/check.py`, run with `env/cgst-ana`. The potential
comes from `common/model.sh` (`MODEL_ID`, set it in the environment for a non-default one) and the compiled file for
the node from `common/defaults.sh`; LAMMPS runs go through `common/run_lmp.sh`. Every test rewrites its `RESULT*.txt`
in place: `tests/collect.sh --save <MODEL_ID> "<since>"` copies a potential's verdicts to `tests/results/<MODEL_ID>/`
with the job and time of each (`INDEX.txt`; check its job IDs, which are taken from the newest Slurm log).

## Tests

| label | directory | what it checks | pass |
|---|---|---|---|
| 1b | `model_check/` | the compiled file against the checkpoint (`nequip.integrations.ase.NequIPCalculator`, float64) on 13 held-out DFT test frames (144–768 atoms, 0–77 C, orthorhombic and triclinic): energies, forces and the virial pressure tensor; also writes the reference energies the other builds are compared with, and the checkpoint-vs-DFT energy errors | \|ΔE\| ≤ 1e-6 eV/atom |
| — | `model_select/` | `common/defaults.sh` picks the node type's own file from the hostname, and it gives the same energies as 1b on the 13 frames | selected; max \|ΔE\| = 0 |
| 1a | `smoke/` | 1×1×1 x0 and x10 cells: minimize, NPT 600 K for 2 ps at 1 fs, a 1 ps RDF window; the thermo columns, RDF block and gzipped dump are written and finite; `analysis/bondorder.py` matches LAMMPS's `c_ncb` (`check_smoke.py`) | x0 and x10 finish, no lost atoms |
| 1c | `dt/` | NVE energy conservation at 0.5, 1 and 2 fs from the same 1500 K x10 liquid (2×2×2, 4096 atoms; `analyze_dt.py`) | drift ≤ 0.05 meV/atom/ps and std(E_tot)/std(PE) ≤ 0.01 at the production `DT` |
| — | `compile_check/` | a fresh `models/compile_model.sh` compile against the production file on the 13 frames | max \|ΔE\| = 0 (the bytes differ: AOTInductor output is not byte-reproducible) |
| 1f | `container/` | `lammps_stable.sif` against `lammps_debug.sif` through the production launch path: energies on the 13 frames and a 1-GPU benchmark | identical energies |
| 1h | `stress_parity/` | model vs DFT static pressure and energy on every held-out test frame, per config type | report (no threshold) |
| 1j | `am_eos/` | model vs DFT equations of state on the training EOS sets (one structure rescaled to ~24 volumes, fixed fractional coordinates): zero-pressure density and pressure error | report |
| 1g | `density/` | x0 rocksalt 3×3×3 at NPT 300 K, 0 bar: the crystal's V/atom and density, for the glass–crystal comparison | report |
| 1i | `glass_relax/` | 12 held-out DFT frames per class (melt-quench glass, amorphous, cubic) relaxed with the model at NPT 300 K, 0 bar for 20 ps | report |
| 1k | `dft_glass/` | the model's own 10 K/ps x0 glass (`make_model_glass.py`) against the coldest frames of DFT's NPT melt-quench (`GST_Melt_Quench_Eform_train.xyz`): density and per-species coordination, with the same code and cutoffs (`analysis/mq_structure.frame_stats`) | CONSISTENT: \|Δρ\| < 2% and every \|ΔZ\| < 0.15 |
| 1d/1e | `scaling/` | throughput: `submit_size.sh` (333 vs 444 cells, 1/2/4 A100s, peak GPU memory) and `submit_all.sh` (1 and 2 GPUs per partition, analysis on/off) | sets `SIZE`/`NGPU` and the budgets |
| — | `mq_logic/` | the melt-quench input on short runs: `tmelt`, the MSD gate and a gate that fails on purpose | `VERDICT: PASS` |
| — | `recryst_logic/` | the recrystallization inputs and analysis: ramp and ramp restart, anneal and resume, halt, calibration, the analysis' known answers | `VERDICT: PASS` |
| — | `mq_analysis/` | `analysis/mq_summary.py` and `mq_structure.py` on reference copies (`ref/`, with `SHA256SUMS`), incl. the closest-approach check | PASS |
| — | `env_probe/` | the container's LAMMPS build and styles (`probe.sh`; reconstructs a probe first run by hand) | — |
| — | `tuning/` | `comm_modify cutoff` 7.0 vs 7.5 and `PMIX_MCA_psec=native` | — |
| — | `a100_model/` | recompiles the checkpoint on an A100 node and compares with `model_check/lammps_energies.txt`; superseded by compiling every node type's file directly (`RUNBOOK.md`, A2) | identical energies |
| — | `latent_feasibility/` | exploratory: Allegro latent features vs Q4 for crystallinity (`README.md` there) | — |

## Environment (independent of the potential)
- **Container** (`env_probe/`): `lammps_debug.sif` is LAMMPS 30 Mar 2026, Kokkos 5.0.2 (CUDA + Serial, double), with
  the packages KOKKOS KSPACE MOLECULE PYTHON REAXFF plus `pair allegro/kk`. The styles this project needs are present:
  `orientorder/atom/kk`, `coord/atom/kk`, `cluster/atom`, `rdf`, `msd`, `rerun`, `fix halt`. It has no `custom/gz`
  dump style, but it is built with `-DLAMMPS_GZIP`, so a dump named `*.gz` is piped through gzip (checked by 1a).
  Its host code is an `-O0` debug build (`models/provenance.md`, Container), which costs nothing measurable: the model
  evaluation dominates, and `lammps_stable.sif` runs at the same speed with identical energies (1f).
- **Launch path:** both containers work through `common/run_lmp.sh` (srun, one rank per GPU). Started without srun
  (or from an interactive `srun bash` step) they abort in `MPI_Init` or print only PMIx/munge errors: Open MPI sees
  the Slurm environment and lacks Slurm PMI support.
- **A compiled model runs only on the CPU type it was compiled on.** On another node type `lmp` dies with
  `Illegal instruction` inside the `torch::inductor::AOTIModelContainerRunner` constructor, the AOT model loader; a
  file compiled on that node type works and gives identical energies. Hence one file per node type, chosen by
  `common/defaults.sh` from the hostname: A30 b-nodes (and d-nodes, assumed to accept the b-node file; not yet
  checked for the current potentials), a100-40gb g-nodes (AMD EPYC 7662) and n-nodes (AMD EPYC 7413), a100-80gb
  k-nodes. a100-80gb i-nodes have no file. The GPUs are all compute capability 8.0 (sm_80).
- **Slurm:** when `--mem` forces more CPUs than `--cpus-per-task`, `srun` aborts with `cpus-per-task set by two
  different environment variables`; `run_lmp.sh` unsets `SLURM_TRES_PER_TASK` and passes `--cpus-per-task`
  explicitly. On perc g-nodes LAMMPS can die in `MPI_Init` (PMIx `gds_ds12` lock): `RUNBOOK.md`, cluster note.
- **Never edit a script a running job reads.** bash reads scripts as it goes; an in-place edit of `run_lmp.sh` during
  a job made bash read the new file at a stale offset and fail after LAMMPS had finished. Replace such files
  atomically (write a temp file, then `mv`); `run_lmp.sh` `exec`s srun for the same reason.
- **x10 rocksalt is not a crystal reference:** with no vacancies and C on octahedral cation sites it disorders within
  a few ps at 600 K (1a, nequip_no_zbl: crystal fraction 0.93 → 0.57 in 3 ps, while x0 stays at 0.94).

## Timestep criteria (1c)
The thresholds were fixed before the first run and are conventional, not derived (`dt/analyze_dt.py`): drift ≤ 0.05
meV/atom/ps (5 meV/atom per unthermostatted 100 ps, about 4% of kT at 1500 K) and std(E_tot)/std(PE) ≤ 0.01
(integration error at least 100× below the physical PE fluctuations). Margin = threshold / observed. The chosen value
goes into the model's block in `common/model.sh` (`DT`).

## Analysis environment (`env/`)
`env/environment.yml` → `env/cgst-ana` (exact build: `env/environment.lock.txt`): python 3.12, numpy 2.2.6,
scipy 1.15.2, matplotlib 3.10.9, OVITO 3.17.2 (from conda.ovito.org). Each package names its consumer in the yml.
`tests/model_check` uses ase, which comes from the container, not this environment.
- The home quota (25 GB) is small, so the conda package cache must live on scratch: `CONDA_PKGS_DIRS`.
- conda-forge's `ovito` package is the desktop app without the Python module, so the channel is pinned.

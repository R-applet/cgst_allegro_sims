# Part 1 test results

Each test directory has a batch script, run from inside that directory with `sbatch`: `submit.sh`, except
`scaling/submit_all.sh` (plain bash, submits the jobs itself) and `env_probe/probe.sh`. These are Part 1 tests;
`mq_logic/` and `recryst_logic/` test the Part 2/3 inputs and are reported in those parts' READMEs.
LAMMPS runs go through `common/run_lmp.sh` with `models/run5_ep301.nequip.pt2` and `lammps_debug.sif`. Exceptions:
1f also runs `lammps_stable.sif` (via `SIF`), the compile check runs a recompiled model, and Python steps (1b
`prepare`, `models/compile_model.sh`) use `apptainer exec` directly.

## Environment probe (`env_probe/`)
`probe.sh` reconstructs the probe, which was originally run by hand; the script itself has not been run yet.
- `lammps_debug.sif`: LAMMPS 30 Mar 2026, Kokkos 5.0.2 (CUDA + Serial, double), packages KOKKOS KSPACE MOLECULE
  PYTHON REAXFF plus `pair allegro/kk`. The styles this project needs are present: `orientorder/atom/kk`,
  `coord/atom/kk`, `cluster/atom`, `rdf`, `msd`, `rerun`, `fix halt`. It has no `custom/gz` dump style, but it is
  built with `-DLAMMPS_GZIP`, so a dump named `*.gz` is piped through gzip (checked in the smoke test).
- `lammps_stable.sif`: started from inside an interactive `srun bash` step, it printed only PMIx/munge errors and
  no LAMMPS banner (`lmp_help_stable.txt`); `lammps_debug.sif` printed the same errors, then ran. Through the
  production launch path both work (1f).
- GPUs: the A30 on gilbreth-b006 reports compute capability 8.0, matching the sm_80 compiled model. Every A30 job so
  far ran on b-nodes (b003, b006, b008, b013) or, since 1d, d-nodes (d000, d005).
- **A100 nodes: the production model file crashes there; a model recompiled on the A100 node works.**
  - With `models/run5_ep301.nequip.pt2`, `lmp` dies with `Illegal instruction` inside the
    `torch::inductor::AOTIModelContainerRunner` constructor (the CUDA subclass on a100-40gb), the AOT model loader. Seen on a100-80gb k022 and i002
    (jobs 12234302, 12234705) and on a100-40gb g000, n000 and n002 (jobs 12235961, 12235963, 12235964).
  - Recompiled with `models/compile_model.sh` *on* the A100 nodes, the model runs on both a100-40gb node types
    (`a100_model/`, jobs 12236152 G on g000, AMD EPYC 7662; 12236153 N on n019, AMD EPYC 7413). Energies are
    identical to production on all 13 model_check frames.
  - So the model's host code is tied to the CPU of the node it was compiled on (production: an A30 b-node). The b-node
    CPU and the exact missing instructions were not checked.
  - 1 GPU, 13824 atoms, analysis on: **2.93 ns/day (G) and 3.13 ns/day (N)**, against 1.71 on an A30 (about 1.8×).
  - Promoted to `models/run5_ep301.{G,N}.nequip.pt2`. `common/defaults.sh` selects the file by hostname, and the
    production submit scripts pass it as `-var model`. End-to-end check: `model_select/` (see below).
- **Slurm quirk**: when `--mem` forces more CPUs than `--cpus-per-task`, `srun` aborts with
  `cpus-per-task set by two different environment variables`. `run_lmp.sh` now unsets `SLURM_TRES_PER_TASK` and
  passes `--cpus-per-task` explicitly.

## Per-node model selection (`model_select/`): PASS (jobs 12239230 on g005, 12239231 on n003)
`common/defaults.sh` resolved `MODEL` from the hostname (G on g005, N on n003, both nodes new to these files). Each
run's model_check energies are identical to production (max |ΔE| = 0, 13 frames). The mapping logic (b/d → A30
file, g → G, n → N, anything else aborts before LAMMPS starts, `MODEL=` overrides) was also checked on the login
node with a stub `hostname`.

## 1a. Smoke (`smoke/`): PASS (job 12234221; rerun after the `nxb`→`ncb` rename: job 12235755; verdict from
`smoke/check_smoke.py` → `smoke/RESULT.txt`)
- The rerun reproduces the original crystalline fractions exactly (same seeds), and `analysis/bondorder.py` still
  matches LAMMPS's `c_ncb` atom for atom (max |Δncb| = 0 on every frame of both dumps).
512-site x0 (no C) and x10 (51 C) cells: minimize, then NPT 600 K for 2 ps at dt = 1 fs, then a 1 ps RDF window.
- No errors or lost atoms; PE finite. `smoke_<cell>.dat` has all 13 columns; `msdC` is 0 for x0 (empty-C guard works).
- `rdf_<cell>.dat` has one block of 300 rows at step 3000. Pairs involving C are 0, not NaN, when there is no C.
- `smoke_x10.lammpstrj.gz` is written and readable, with per-atom `c_q4[1]` and `c_ncb`.
- Physics note: at 600 K, x0 rocksalt stays crystalline (xfrac 0.94 → 0.94), but x10 (no vacancies, C on octahedral
  cation sites) disorders within 3 ps (xfrac 0.93 → 0.56; C MSD 2 Å²). The x10 starting crystal is mechanically
  unstable. This doesn't affect the melt-quench, but x10 cannot serve as a crystalline reference in Part 3.

## 1b. Model check (`model_check/`): PASS (energies and forces: job 12234242; pressure tensor added: job 12235720)
13 test-set frames (one per size/C-content class: 144–768 atoms, 0–77 C, orthorhombic and triclinic), comparing
LAMMPS `run 0` against the checkpoint evaluated through `nequip.integrations.ase.NequIPCalculator` (float64, CUDA).
- |ΔE| < 5e-5 meV/atom (below the printed precision) and max |ΔF| ≤ 2.2e-11 eV/Å on every frame (`model_check/RESULT.txt`).
  The compiled model reproduces the checkpoint exactly.
- Pressure tensor (virial only; zero velocities): max |ΔP| ≤ 5.4e-3 bar on every frame, against components of
  about 10²–10⁴ bar (`model_check/RESULT.txt`). That confirms the sign (P = −stress) and Voigt-order mapping
  as well. The barostat sees the same virial the checkpoint predicts.
- For context, model − DFT energies on these frames range from −9.1 to +9.7 meV/atom.

## 1c. Timestep (`dt/`): PASS at 2 fs → **production dt = 2 fs** (job 12234297)
2×2×2 x10 (4096 atoms, 408 C, the most C-rich state) as a liquid after 20 ps NPT at 1500 K, then 20 ps NVE per dt
from the same state (`dt/RESULT.txt`):

| dt (fs) | ⟨T⟩ (K) | drift (meV/atom/ps) | drift margin | std(E_tot)/std(PE) | ratio margin | E_tot range over 20 ps (meV/atom) |
|---|---|---|---|---|---|---|
| 0.5 | 1563 | −0.0001 | 697× | 0.0004 | 27× | 0.009 |
| 1.0 | 1554 | −0.0004 | 139× | 0.0013 | 7.9× | 0.030 |
| 2.0 | 1550 | −0.0011 | 45× | 0.0060 | 1.7× | 0.119 |

Margin = threshold / observed. The thresholds were fixed before the run and are conventional, not derived
(basis in `dt/analyze_dt.py`): drift ≤ 0.05 meV/atom/ps (5 meV/atom per unthermostatted 100 ps, about 4% of kT at
1500 K) and std ratio ≤ 0.01 (integration error at least 100× below physical PE fluctuations).

- **Repeat (job 12235730; `dt/seed2/`): a second velocity seed and 40 ps NVE per dt.** All pass again. 2 fs: drift
  −0.0006 meV/atom/ps (89× margin), ratio 0.0039 (2.6× margin). Both margins are larger than in the first run, so
  2 fs stands.
- All three pass. 2 fs is comfortable on drift (45×) but closer on the fluctuation ratio (1.7×). It is chosen for
  throughput; 1 fs (7.9× margin) is the fallback if a production run shows energy or temperature anomalies. The
  production value lives in `common/defaults.sh`.
- 1 A30, 4096 atoms: 34.5 steps/s (141 katom-steps/s).
- The job shows FAILED in Slurm, but LAMMPS finished all three runs (`log.dt`, "Total wall time 0:43:49"). The
  failure came afterwards: `common/run_lmp.sh` was edited while the job was running it, and bash read the new file
  at a stale offset (syntax error at line 15). `RESULT.txt` was then produced by hand. From now on, files that jobs
  read are replaced atomically (write a temp file, then `mv`), never edited in place while jobs run.

## 1d/1e. Scaling and analysis overhead (`scaling/`): done → **2 A30s per production job; keep on-the-fly analysis**
13824 atoms (3×3×3 x10), NPT 600 K, dt = 2 fs; timed 3000-step run (`python3 scaling/summarize.py`):

| run | ns/day | steps/s | katom-steps/s | job (node) |
|---|---|---|---|---|
| a30, 1 GPU, analysis on | 1.69 | 9.8 | 134.9 | 12234704 (b008) |
| a30, 2 GPUs, analysis on | 3.35 | 19.4 | 267.8 | 12234299 (d005) |
| a30, 2 GPUs, analysis off (1e) | 3.33 | 19.3 | 266.3 | 12234301 (d000) |
| a100-40gb g-node, 1 GPU, analysis on (G model) | 2.93 | 16.9 | 234.0 | 12236152 (g000), `a100_model/` |
| a100-40gb n-node, 1 GPU, analysis on (N model) | 3.13 | 18.1 | 250.2 | 12236153 (n019), `a100_model/` |

- **2 A30s scale at 99% efficiency** (1.98×). That supports the 2-GPU default in the production submit scripts.
- **1e: the on-the-fly analysis costs nothing measurable** (3.35 vs 3.33 ns/day). The `fix STORE/ATOM` Kokkos
  fallback warning (`log.a30_g1_ana1`) has no measurable cost, so the per-species MSD columns stay.
- One A100 ≈ 2 A30s. A100 multi-GPU scaling was not measured: the 2- and 4-GPU A100 benches ran with the
  A30-built model and crashed. The "incomplete" rows in `summarize.py` are those runs and the a100-80gb ones.
  Until A100 scaling is measured, run 1 GPU per job on A100 (it uses the 10 perc GPUs best).
- The 3-GPU a30 run (12234300) was cancelled: strachan's 6-A30 cap, with 4 held long-term by another user, means
  production can never get 3 A30s.
- Both 2-GPU runs landed on a30 d-nodes, so **d-nodes run the A30-built model**, which was untested before.

## Tuning: ghost cutoff and PMIx noise (`tuning/`; job 12235756): no change adopted
13824 atoms, 1 A30, analysis on (`tuning/RESULT.txt`):
- `comm_modify cutoff` 7.5 (current) vs 7.0: 1.702 vs 1.695 ns/day, the same within noise. The 6 Å RDF works at
  7.0 (300 rows). The extra ghost shell costs nothing measurable, so `common/in.potential` keeps 7.5. (The ghost-count
  column of `RESULT.txt` is broken: it parsed the word "ave".)
- `PMIX_MCA_psec=native` cuts the munge/PMIx lines in a run's screen output from 3 to 1. That is too little to
  matter, so `run_lmp.sh` is unchanged.

## 1f. Container comparison (`container/`): PASS; both containers work, `lammps_debug.sif` kept (job 12235514)
Both containers run through the production srun path (`common/run_lmp.sh`, `SIF` swapped), on gilbreth-b003
(`container/RESULT.txt`):

| container | LAMMPS | 13 model_check frames | 13824 atoms, 1 A30, analysis on |
|---|---|---|---|
| `lammps_debug.sif` | 30 Mar 2026 | reference | 1.709 ns/day (9.89 steps/s) |
| `lammps_stable.sif` | 11 Feb 2026 | max \|ΔE\| = 0 eV/atom | 1.708 ns/day (9.88 steps/s) |

- The stable container's start-up failure in the environment probe came from how the probe launched it, not from
  the container.
- The debug image's `-O0` host build (`models/provenance.md`, Container) costs nothing measurable, because the model
  evaluation dominates. The debug image is kept for continuity with the reference runs.
- An earlier attempt (job 12235379) started both containers without srun. Both, debug included, aborted in
  `MPI_Init` (Open MPI sees the Slurm environment and lacks Slurm PMI support), so that run says nothing about either.
- `container/RESULT.txt` was regenerated from the job's logs after fixing its `Performance` grep, which had matched a
  citation line.

## Compile reproducibility (`compile_check/`): PASS (job 12235380)
`models/compile_model.sh` recompiled the checkpoint, and both compiled files then ran on the 13 model_check frames
(`compile_check/RESULT.txt`):
- max |ΔE| = 0 eV/atom.
- The sha256 differs (`886e4f7b…` vs production `0a1a1b31…`). The files are not byte-identical, but numerically
  they are the same model; `provenance.md` keeps the production hash as the reference.

## 1g. Density check (`density/`): **FAIL, amorphous denser than crystal** (job 12235695)
The same model (run5_ep301) at NPT 300 K and 0 bar:

| state | V (Å³/atom) | ρ (g/cc) | source |
|---|---|---|---|
| rocksalt crystal, x0 3×3×3 (12447 atoms) | 30.381 (⟨P⟩ = −4.8 bar) | 6.238 | `density/RESULT.txt`, 20 ps average after 20 ps |
| amorphous, 10 K/ps melt-quench (7200 atoms) | 30.135 ± 0.024 | 6.287 | reference `md_meltquench/meltquench.dat`, last 50 ps |

- **The model's glass is 0.8% denser than its crystal**, about 10× the glass's own volume fluctuation.
- Experimentally, amorphous GST is about 6–7% *less* dense than the metastable cubic phase (about 5.9 vs 6.3
  g/cc; values from memory, to be checked against the literature). The model crystal (6.24) is close to that
  cubic value, so the error is in the amorphous phase, roughly 7% too dense.
- Small differences between the two cells (2754:2781:6912 here vs exactly 2:2:5 in the reference; one glass
  sample) cannot reverse the sign.
- **Consequence:** in this model, crystallization would expand the sample. The Part 3 strain and driving force are
  qualitatively wrong, and `analysis/recryst_summary.py`'s `Tx_rho` (which assumes densification) is invalid.
  **No production runs until this is resolved.**
- **Next check:** model pressure vs DFT stress on the amorphous and crystal DFT frames. That separates a fitting
  error (fix the model) from a property of the reference DFT (revisit the training data).

## 1h. Model vs DFT pressure on the test set (`stress_parity/`; job 12237039 on a perc A100)
Static (virial-only) pressures on identical held-out structures, P = −tr(σ)/3 (`stress_parity/RESULT.txt`,
per frame in `frames.csv`):

| config type | n | V (Å³/atom) | P_DFT (kbar) | P_model − P_DFT (kbar) |
|---|---|---|---|---|
| AM_GST_runs | 767 | 31.12 | +12.90 | −2.02 |
| CUB_GST_runs | 271 | 30.53 | +8.11 | −1.61 |
| HEX_GST_runs | 249 | 30.03 | +6.66 | −0.90 |
| GST_Melt_Quench | 51 | 32.70 | −2.09 | −1.86 |
| C-containing sets | 10–132 each | 26–63 | — | mostly −2 to −5 |

- **The model's pressures are systematically low by ~1–5 kbar** (more so with C). With bulk moduli of ~30–40 GPa
  that is a 0.4–0.7% density excess, nearly the same for glass and crystal (a difference of ~0.4 kbar). **It
  explains only a fraction of a percent of 1g's ~7% glass-density error.**
- **The DFT glasses themselves are near the experimental density.** GST_Melt_Quench frames sit at 32.7 Å³/atom
  (5.79 g/cc for 2:2:5) with a DFT virial of −2.1 kbar (≈ 0 total once the thermal pressure is added; frame
  temperatures unknown, so this is an estimate). AM_GST_runs at 31.1 Å³/atom has a DFT virial of +12.9 kbar,
  meaning it wants to expand.
- **Reading (a hypothesis):** the model reproduces DFT on DFT-sampled glasses, but its own melt-quench finds
  denser amorphous structures that are not in the training data and where its energies are wrong (a hole in the
  potential-energy surface). Neither a fitting bias on the training distribution nor the DFT reference is the
  main cause.
- **Checks to confirm:**
  1. Relax the DFT GST_Melt_Quench frames with the model at NPT 300 K and 0 bar, and see whether they collapse
     toward 6.3 g/cc.
  2. DFT single points on the model's own glass (Rushik's `md_mq144` snapshots).

## 1i. DFT frames relaxed with the model (`glass_relax/`; job 12237525 on a perc A100 n-node)
12 held-out DFT frames per class (144-atom cells), each run with the model (n-node recompile) at NPT 300 K, 0 bar
for 20 ps, density averaged over the last 10 ps (`glass_relax/RESULT.txt`):

| class | ρ of the DFT frame (g/cc) | ρ after model NPT (g/cc) | change |
|---|---|---|---|
| GST_Melt_Quench (DFT glasses) | 5.86 ± 0.32 | 6.27 ± 0.04 | +7.3% |
| AM_GST_runs | 6.19 ± 0.16 | 6.29 ± 0.03 | +1.7% |
| CUB_GST_runs (crystal control) | 6.22 ± 0.09 | 6.27 ± 0.01 | +0.8% |

- **Every class ends at 6.27–6.29 g/cc, the density of the model's own melt-quenched glass (6.287, 1g).**
- DFT's pressures say its glasses are near equilibrium at about 5.8 g/cc (1h). So the model's potential-energy
  surface drives amorphous GST about 7% denser than the DFT supports. That supports 1h's reading: a model
  (training-coverage) problem, not the workflow and not the DFT reference.
- **Caveat:** the DFT frame temperatures are unknown. Some melt-quench frames are probably hot (the spread in
  starting density is ±0.32), and cooling them densifies them in any potential. The definitive check is DFT single
  points on the relaxed structures.
- **For DFT (job 12238032, a rerun with `write_data`):** `glass_relax/relaxed_for_dft.xyz` holds 36 relaxed
  144-atom structures with metadata; `glass_relax/README_for_DFT.md` is the request and how to read the answer.
  The rerun reproduces the class densities within 0.003 g/cc (first run kept in `glass_relax/run1/`; GPU runs on
  different nodes are not bit-identical).

## 1j. Model vs DFT equations of state on the training EOS frames (`am_eos/`; job 12252986 on a perc A100)
Each `*_EOS_Eform_train.xyz` set (from `/depot/prism/data/rapplet/cgst-vasp-data/xyz_files/train/`) is one
144-atom structure (plus C), rescaled uniformly to ~24 volumes, with fixed fractional coordinates and unrelaxed ions
(the amorphous frame has F_max ≈ 1.5–3 eV/Å, a thermal snapshot). The zero crossing of the static P(V) (cubic fit)
gives the following (`am_eos/RESULT.txt`, per frame in `frames.csv`):

| set | ρ0 DFT (g/cc) | ρ0 model (g/cc) | model − DFT | P bias (kbar) |
|---|---|---|---|---|
| GST_AM_EOS | 6.142 | 6.169 | +0.44% | −1.9 |
| GST_CUB_EOS | 6.303 | 6.300 | −0.04% | +4.0 |
| GST_HEX_EOS | 6.385 | 6.353 | −0.51% | +5.3 |
| C1/C5/C10/C14/C18 AM_EOS | 6.13 / 6.16 / 6.12 / 6.11 / 6.06 | | +0.41 to +0.62% | −1.9 to −3.3 |
| C1/C5/C10 CUB_EOS | 6.35 / 6.46 / 6.62 | | −0.34 / −0.84 / −1.61% | +5 to +10 |

- **The model reproduces DFT's EOS on these structures** (these frames are training data). The amorphous zero is
  0.4–0.6% too dense, consistent with 1h's ≈ −2 kbar bias. For GST, the fitting error narrows the glass–cubic gap
  by only ≈ 0.5% (amorphous +0.44%, cubic −0.04%). With C, the crystal shifts grow to −1.6% (C10 cubic).
- **DFT puts this amorphous structure 2.6% less dense than the cubic crystal** (6.14 vs 6.30 static). That is
  smaller than the experimental ~6–7%, so part of 1g's "7% error" is the DFT reference, not the model. Measured
  against DFT, the model glass (6.287 at 300 K) is ≈ 2.4% too dense (≈ 3% after a thermal correction of a few
  tenths of a percent to the static value).
- **Reading:** the model is right on the structure it was fitted to, yet its MD relaxes amorphous GST to ≈ 6.29
  (1g, 1i). The excess density therefore comes from the structural relaxation, which a frozen-ion EOS does not
  sample. This is still consistent with 1h's PES-hole hypothesis, but the EOS cannot tell whether DFT would relax the
  same way. Only DFT on the relaxed structures (`glass_relax/relaxed_for_dft.xyz`) can settle that.

## Analysis environment (`env/`)
`env/environment.yml` → `env/cgst-ana` (exact build: `env/environment.lock.txt`): python 3.12, numpy 2.2.6,
scipy 1.15.2, matplotlib 3.10.9, OVITO 3.17.2 (from conda.ovito.org). Each package names its consumer in the yml.
`tests/model_check` uses ase, which comes from the container, not this environment.
- Home quota (25 GB) is full, so the conda package cache must live on scratch: `CONDA_PKGS_DIRS`.
- conda-forge's `ovito` package is the desktop app without the Python module, so the channel is pinned.

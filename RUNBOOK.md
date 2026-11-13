# Runbook: the full workflow for a new potential

This is the order of steps to run everything from scratch with a new (retrained) model, with what each step must
show before the next one starts. The method behind each step is in the part READMEs; this file only sequences them.
Every number a step measures goes into `params/<MODEL_ID>.sh` or is generated into
`recryst/calib/<MODEL_ID>/calib_params.sh`. No script holds a model's values, and no run of one model shares a
directory with another (`runs/<MODEL_ID>/`, `results/<MODEL_ID>/`, `calib/<MODEL_ID>/`).

**Requirements.** Gilbreth (Purdue) with read access to `/depot/prism` (container, model sources, DFT data), the
`strachan` and/or `perc` Slurm accounts, and `env/cgst-ana` for analysis (`README.md`, Running). Every `sbatch` is a
separate go-ahead: run `--dry-run` first where a script offers it. Heavy analysis (`--clusters`, `mq_structure.py`)
runs as an `sbatch` job, not on a login node.

The previous model, run5_ep301, is archived at git tag `run5_ep301-final`. Its outputs are in the `run5_ep301/`
subdirectories, and its results are in `meltquench/results/run5_ep301/RESULTS.md`,
`recryst/results/run5_ep301/RESULTS.md` and `tests/RESULTS.md`. Use them for comparison, never as settings.

## Part 0: register the model
1. In `common/model.sh`, add a `case` block for the new `MODEL_ID` (CKPT, MODEL_SRC, TRAIN_DIR; SIF if the container
   changes). Then set the default `MODEL_ID` to it, or `export MODEL_ID=...` in every shell and job.
2. Compile one file per node type, each on a node of that type (`common/defaults.sh` picks by hostname):
   - b/d-node A30: `cd models && sbatch compile_model.sh $PWD/<MODEL_ID>.nequip.pt2`
   - g- and n-node A100: `cd tests/a100_model && sbatch --constraint=G --export=ALL,NODE=G submit.sh` (likewise `N`),
     then copy `<MODEL_ID>.G.nequip.pt2` and `<MODEL_ID>.N.nequip.pt2` to `models/`.
   Record the sources, sha256s and nodes in `models/provenance.md`.
3. `cp params/run5_ep301.sh params/<MODEL_ID>.sh`. Mark every value as to-be-measured: each is replaced in the steps
   below, and a value left from run5_ep301 is wrong until a step confirms it.

**Pass:** `source common/defaults.sh` resolves `MODEL` on each node type (`tests/model_select`, both constraints).

## Part 1: model and environment tests (`tests/`)
The Part 1 records will be overwritten in place (`RESULT.txt` in each directory; run5_ep301's are at the tag).
Write this model's summary to `tests/RESULTS_<MODEL_ID>.md`, in the format of `tests/RESULTS.md`.
1. Correctness: `model_check` (compiled vs checkpoint energies and forces), `compile_check`, `smoke`, `container`.
   **Pass:** energy agreement at 1e-6 eV/atom; smoke runs finish on x0 and x10.
2. Timestep: `dt` (NVE drift at 0.5/1/2 fs in the 1500 K x10 liquid). **Pass:** 2 fs conserves energy, otherwise set
   `DT` in `common/defaults.sh` and note it.
3. Throughput: `scaling`. Update the Budget sections if ns/day changed.
4. Physics against DFT: `stress_parity`, `am_eos`, `density`, `glass_relax`. For `dft_glass` (1k), first make this
   model's own 10 K/ps glass (Part 2) and pass it as `MODEL_GLASS`. **Decide here** how the glass density compares
   with the crystal's (run5_ep301: glass denser, from its DFT reference); this sets the caveats of everything after.
5. Logic tests of the inputs: `tests/mq_logic` and `tests/recryst_logic` (GPU, short). These also cover the new
   `tmelt` and `tmax` inputs and `ramp_done.txt`, which no GPU job has exercised yet. **Pass:** `VERDICT: PASS` in both.

## Part 2: melt-quench (`meltquench/`)
1. **Superheating pilot (sets `TMELT`).** The melt must be far above the model's superheated melting point. For
   run5_ep301 the crystal melted at ~1090 K at 2 K/ps, and Tm_app on the 10 K/ps heat was 984–1129 K. Run one x0 and
   one x10 melt-quench (`sbatch --array=0,12 submit.sh`) and read Tm_app from `analysis/mq_summary.py`.
   **Pass:** `TMELT` (a multiple of 100) is at least ~300 K above the highest Tm_app, and the MSD gate passes. If not,
   raise `TMELT` or `HOLD_PS` in params and rerun those two.
2. Production: `sbatch --array=0-14 submit.sh` (5 compositions × 3 replicas at `QRATE`). **Pass:** all 15 pass the
   MSD gate with one `HOLD_PS`.
3. Analysis (sbatch for `mq_structure.py`), outputs in `meltquench/results/<MODEL_ID>/`. Record density, Tm_app, Tg and
   `xfracGST` per composition in `meltquench/results/<MODEL_ID>/RESULTS.md`. Optional 1 K/ps sensitivity runs
   (`--array=0,12 --export=ALL,QRATE=1`): run5_ep301's partially crystallized, which is why Part 3 uses 10 K/ps.

## Part 3: recrystallization (`recryst/`)
1. **Calibration (generates the criterion and per-T tables).** `cd recryst/calib && sbatch --array=0-53 submit.sh`,
   then `sbatch submit_calibrate.sh`. Read `calib/<MODEL_ID>/calibrate.out` and `calib.png`. If the best criterion
   is not clearly better than a neighbour, rerun with `--export=ALL,CALIB_ARGS="--choose RC THR NMIN"`.
   `calib_params.sh` is regenerated each time. **Pass:** a crystal/glass margin comparable to run5_ep301's 0.71, no
   edge-of-grid warning, and `calib_params.sh` covering every temperature you will anneal at.
2. **Ramp (sets `TX_GUARD` and centres the grid).** `cd recryst && sbatch --array=0 submit_ramp.sh` (x0 r1 at
   `HRATE` 0.2 K/ps to `TMAX`; on the A30s, since it exceeds 24 h on one A100). `TMAX` must stay below the
   superheated melting point from Part 2. Then `bash scripts/analyze_ramps.sh`. **Read:** whether and where x0
   crystallizes (Tx_xfrac). Set `TX_GUARD` to a Tx measured at a heating rate comparable to the anneals' 10 K/ps
   heat, or to `TMAX` if none exists (run5_ep301: 900). The slow-ramp Tx is not the guard. If nothing crystallizes by
   `TMAX` even at 0.2 K/ps, expect the anneal grid to be TOO COLD and plan the seeded slabs (step 5) as the main
   route.
3. **Phase A pilot: x0 over the grid (sets `XSTOP`, `X_END` and checks `BARO`).** Set `TAS` to calibration
   temperatures that bracket the ramp's Tx. Use `XSTOP`/`X_END` provisionally at 0.65; `BARO=aniso` and
   `RUNTAG=""` unless an iso comparison is wanted. Run `CELLS=x0 bash scripts/submit_grid.sh --dry-run`, then
   without `--dry-run`. Afterwards run `bash scripts/analyze_grid.sh summary`, then `verdict` once the cluster job is
   done.
   **Read and set:**
   - the plateau `xfracGST` that grown crystals reach. Set `XSTOP` below it and `X_END` ≤ `XSTOP`, the same for
     every Ta; if runs ran with a different value, rerun or accept one `XSTOP` per set;
   - the Ta that are USABLE;
   - `sdev_z` under the chosen barostat;
   - `single_grain`: below 0.8, `v_growth` is an upper bound.
   **Pass:** at least two USABLE Ta for x0, and `XSTOP` set from data.
4. **Phase B: every composition.** Set `TAS` to the window where nucleation happens, then run
   `bash scripts/submit_grid.sh --dry-run` and the same analysis. Phase A's x0 runs are reused. Outputs:
   `results/<MODEL_ID>/growth_table.csv` and `grid_verdict.txt`. Add replicas (`NREP`) where the spread hides a trend.
5. **Seeded slabs (heterogeneous; the full v(Ta) curve).** These are for x0, x1 and x2p5 (x5 and x10 have no stable
   crystal), over 500–900 K or up to the model's Tm. Homogeneous runs give v only where a nucleus forms within
   `MAX_NS`, so the seeded runs supply the peak's high side and v → 0 at Tm (`recryst/README.md`, "Homogeneous vs
   seeded v(Ta)"). If Phase A shows a narrow homogeneous window, make the seeded slabs the primary v(Ta)
   measurement. **Not implemented yet**: `in.seedprep`, the seeded anneal input and their logic test still have to
   be written. Design notes:
   - freeze the central third of the rocksalt along z and melt-quench the rest, with only the mobile group
     thermostatted;
   - set the in-plane box from the calibration crystal's V/atom at Ta, and couple the barostat to z only;
   - halt when the slab is full or the crystal fraction falls below the glass value + 0.03;
   - take v = dN/dt / (2 A n) from the crystalline cluster connected to the seed, and flag stray nuclei.
6. **Write-up:** `recryst/results/<MODEL_ID>/RESULTS.md` (v_growth vs Ta per composition with n per point, its
   distribution, the fraction nucleated vs Ta; then the seeded curve). Plots follow the dataviz conventions.

## What carries over, and what does not
- Carries over: the inputs, scripts, analysis code and their tests; the Q4 criterion *form* (Ge/Sb/Te only); the
  10–60% v_growth window (a geometric result); the 1/√n error estimates.
- Remeasured for every model: everything in `params/<MODEL_ID>.sh` and `calib_params.sh`, plus the timestep, the
  throughput, and the glass-vs-crystal density relation.

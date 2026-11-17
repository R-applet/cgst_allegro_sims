# Runbook: a new potential, from registration to the studies

The order of steps for a potential, with what each step must show before the next starts. The method behind each
step is in the study READMEs; this file only sequences them. Every number a step measures goes into
`<study>/params/<MODEL_ID>.sh` (or is generated, `recryst/calib/<MODEL_ID>/calib_params.sh`), and every run and result
of one potential lives under its `MODEL_ID` (`<study>/runs/<MODEL_ID>/`, `<study>/results/<MODEL_ID>/`).

**Requirements.** Gilbreth (Purdue) with read access to `/depot/prism` (container, checkpoints, DFT data), the
`strachan` (A30), `perc` (A100-40GB) and/or `alta` (A100-80GB) Slurm accounts, and `env/cgst-ana` for analysis (`README.md`, Running).
Every `sbatch` is a separate go-ahead: run `--dry-run` / `sbatch --test-only` first. Heavy analysis
(`--clusters`, `mq_structure.py`) runs as an `sbatch` job, not on a login node. Select the potential with `MODEL_ID`
(default in `common/model.sh`; `MODEL_ID=<id>` before a command or in the shell for another one).

**Current comparison: `nozbl_paw` vs `zbl_paw`** (same training data, without and with per-pair ZBL); each result is
compared with DFT and with the other potential's. Historical: run5_ep301 (tag `run5_ep301-final`; results in
`tests/RESULTS.md`, `tests/results/run5_ep301/`, `meltquench/results/run5_ep301/`, `recryst/results/run5_ep301/`),
kept for reference only, never as settings or pass benchmarks. The examples and benchmarks below are nozbl_paw's.

**Status of `nozbl_paw` (2026-11-16):** A done (A30, G, N and K files); B done, all pass
(`tests/results/nozbl_paw/RESULTS.md`); meltquench done (15 runs at 10 K/ps, analysis in
`meltquench/results/nozbl_paw/`; x0/x10 at 5 and 1 K/ps done; report in `report/`); recryst: calibration done (criterion
3.9/0.6/4), x0 ramp and Phase A done, x5/x10 ramps running; Phase B running for x1 and x2p5 (500–700 K, the same window for every composition; x5/x10
join after their ramps); phases done (`phases/results/nozbl_paw/RESULTS.md`).

**Status of `zbl_paw` (2026-11-17):** A done (A30, G, N and K files, `models/provenance.md`); short gate passed
(B1 `model_check`, `model_select` on all four node types; `tests/results/zbl_paw/RESULTS.md`); phases done
(`phases/results/zbl_paw/RESULTS.md`). Next, before any melt-quench: smoke, dt and the rest of B. Select it with
`MODEL_ID=zbl_paw`; the default stays `nozbl_paw` (running chains source `common/model.sh`).

**Cluster note (PMIx).** On perc g-nodes LAMMPS under `srun` can die in `MPI_Init` with a segfault in PMIx
(`gds_ds12_lock_pthread`; zbl_paw's first two `model_check` jobs, 2026-11-16). Submitting with
`--export=ALL,PMIX_MCA_gds=hash` avoids it, and does nothing elsewhere; set `PMIX_MCA_gds=hash` in the shell for
scripts that submit with `--export=ALL` (`recryst/scripts/submit_grid.sh`). A lone `PMIX ERROR` line in a log that
otherwise runs is harmless.

## A. Register the potential
1. In `common/model.sh`, add a `case` block for the new `MODEL_ID`: `CKPT` (copy the checkpoint into `models/` so a
   resumed training run cannot change it), `TRAIN_DIR` (where the checkpoint's relative dataset path resolves),
   `MODEL_SRC` only if the model needs sources other than the container's, and a provisional `DT`. Register it in
   `models/provenance.md` (checkpoint hash, config, training versions).
2. Compile one file per node type, each on a node of that type (`common/defaults.sh` picks by hostname). The A30
   queue was ~4 days on 2026-11-13 while perc started at once, so the A100 files come first and the A30 file is only
   needed before running on the A30s (`P` = the perc resources):
   ```
   P="-A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1"
   cd models && sbatch $P --constraint=G compile_model.sh $PWD/nozbl_paw.G.nequip.pt2     # g-nodes
   cd models && sbatch $P --constraint=N compile_model.sh $PWD/nozbl_paw.N.nequip.pt2     # n-nodes
   cd models && sbatch --constraint=B compile_model.sh $PWD/nozbl_paw.nequip.pt2          # A30 b/d-nodes, later
   cd models && sbatch -A alta -p a100-80gb --constraint=K compile_model.sh $PWD/nozbl_paw.K.nequip.pt2  # k-nodes
   ```
   Each prints the file's sha256 in its `slurm-*.out`; record file, node and hash in `models/provenance.md`.
   (`tests/a100_model` also compiles G/N and compares with `tests/model_check/lammps_energies.txt`; that file holds
   the energies of the last potential B1 ran for, so don't use it before B1 has run for the new one.)
3. Give each study you will run a `params/<MODEL_ID>.sh`, copied from nozbl_paw's and marked PROVISIONAL: each value
   is replaced by the study's pilot, and a value left from another potential is wrong until a step confirms it.
   (`nozbl_paw`: `meltquench/params/nozbl_paw.sh`.)

**Pass:** `tests/model_select` resolves and runs `MODEL` on both A100 node types
(`cd tests/model_select && sbatch --constraint=G submit.sh; sbatch --constraint=N submit.sh`), with energies equal to
B1's; for the A30 file, B1 and B2 on `--constraint=B` (and smoke on `D`) once it exists.

## B. Validate the potential (`tests/`)
Tests rewrite their `RESULT*.txt` in place. Save the previous potential's first (`tests/collect.sh --save <old ID>`;
run5_ep301's, nozbl_paw's and zbl_paw's gate are saved), and this one's when done (`--save <MODEL_ID>`), with a summary in
`tests/results/<MODEL_ID>/RESULTS.md` in the format of `tests/RESULTS.md`.

**Gate before any study (minimal), on perc with the G/N files from A2:**
1. `model_check`: compiled file vs checkpoint, energies and forces on the DFT test frames; it also writes the
   reference energies the other builds are compared with.
   `cd tests/model_check && sbatch $P --constraint=G submit.sh`. **Pass:** agreement at 1e-6 eV/atom (`RESULT.txt`);
   the checkpoint-vs-DFT errors there are the first look at this potential's accuracy.
2. `smoke`: `cd tests/smoke && sbatch $P --constraint=G submit.sh`. **Pass:** x0 and x10 finish.
3. `dt`: NVE energy drift at 0.5/1/2 fs in the 1500 K x10 liquid. `cd tests/dt && sbatch $P submit.sh`.
   **Pass:** 2 fs conserves energy as well as for nozbl_paw (`tests/results/nozbl_paw/RESULTS.md`, 1c: |drift| ≤ 0.0002
   meV/atom/ps at 0.5, 1 and 2 fs). Critical without ZBL: a close
   contact in the hot liquid shows up here as a drift or a crash. Otherwise set a smaller `DT` in this model's
   `common/model.sh` block and rerun.
4. `model_select` on G and N (A2 Pass).

**Alongside (not gating):** `stress_parity`, `am_eos`, `density`, `glass_relax`, `compile_check`, `scaling` (update
the Budget sections if ns/day changed). `dft_glass` (1k) needs this potential's own 10 K/ps x0 glass: after the
melt-quench: `python make_model_glass.py meltquench/runs/<MODEL_ID>/x0_q10_r1 <npz>`, then
`MODEL_GLASS=<npz> python check.py` (in `tests/dft_glass`). **Decide there** how the glass density compares with the crystal's
(nozbl_paw: glass as dense as its crystal; run5_ep301, historical: denser); it sets the caveats of every study after.
**Logic tests** (`tests/mq_logic`, `tests/recryst_logic`, short GPU jobs) cover `tmelt`, `tmax`, `ramp_done.txt` and the
ramp restart: run them for each potential before the first production job of each study (nozbl_paw: both PASS). **Pass:** `VERDICT: PASS`.

## meltquench: melt-quench (`meltquench/`)
1. **Superheating pilot (sets `TMELT`, `HOLD_PS`).** At the params' `SIZE` (444 for nozbl_paw; build the cells with
   `python structures/build_supercells.py --nrep 4`). x0 r1 and x10 r1, which are also production runs (same seeds):
   ```
   cd meltquench && sbatch -A perc -p a100-40gb --gpus-per-node=2 --ntasks-per-node=2 --array=0,12 submit.sh
   python ../analysis/mq_summary.py --out results/nozbl_paw runs/nozbl_paw/*_q10_r1        # env/cgst-ana
   ```
   **Pass:** the MSD gate passes (`gate.txt`); `TMELT` (a multiple of 100) is at least ~300 K above the higher
   Tm_app (nozbl_paw pilot: 1139 K for x0, 983 K for x10); no close-contact WARNING and per-pair `rmin_*` close to
   nozbl_paw's (x10 liquid: C–C 1.08 Å, Ge–C 1.62 Å, Te–C 1.72 Å, Ge/Sb/Te pairs ≥ 1.98 Å; `mq_summary.py` prints
   them per pair); no lost atoms or errors in `log.mq`. Then record the values and their source in
   `meltquench/params/<MODEL_ID>.sh` (no longer PROVISIONAL). If it fails, change `TMELT`/`HOLD_PS`, delete
   `runs/<MODEL_ID>/{x0,x10}_q10_r1` and rerun the pilot.
2. **Production:** the remaining 13 runs with the pilot's settings.
   ```
   cd meltquench && sbatch -A perc -p a100-40gb --gpus-per-node=2 --ntasks-per-node=2 --array=1-11,13-14 submit.sh
   ```
   (`NGPU` = 2 in params: the submit script refuses a job whose rank count differs; 3.6–4.9 h per run at 444 on 2
   A100s. On the A30s (24 GB) use 3 per run, `sbatch --constraint=B --gpus-per-node=3 --ntasks-per-node=3
   --export=ALL,NGPU=3 ...`, as the 5 K/ps runs did; 2 A30s are untested at 444, which needs 23.3 GB per GPU on 2.) **Pass:** all 15 pass the MSD gate with one `HOLD_PS`.
3. **Analysis:** `mq_summary.py` on the login node, `mq_structure.py` as an sbatch job, both `--out
   results/<MODEL_ID> runs/<MODEL_ID>/*_q*_r*`. Record density, Tm_app, Tg, `xfracGST`, `rmin_*` and the structure per
   composition in `meltquench/results/<MODEL_ID>/RESULTS.md`, compared with the other current potential (nozbl_paw ↔
   zbl_paw). Optional 1 K/ps sensitivity runs (`--array=0,12 --export=ALL,QRATE=1`): nozbl_paw's partially
   crystallized (x0 `xfracGST` 0.30 against 0.14 at 10 K/ps), which is why recryst uses 10 K/ps.

## recryst: recrystallization (`recryst/`)
Needs the melt-quench glasses of the same potential and `recryst/params/<MODEL_ID>.sh` (copy nozbl_paw's, PROVISIONAL).
1. **Calibration (generates the criterion and per-T tables).** `cd recryst/calib && sbatch --array=0-53 submit.sh`,
   then `sbatch submit_calibrate.sh`. Read `calib/<MODEL_ID>/calibrate.out` and `calib.png`. If the best criterion
   is not clearly better than a neighbour, rerun with `--export=ALL,CALIB_ARGS="--choose RC THR NMIN"`.
   `calib_params.sh` is regenerated each time. **Pass:** a crystal/glass margin comparable to nozbl_paw's 0.716, no
   edge-of-grid warning, and `calib_params.sh` covering every temperature you will anneal at.
2. **Ramp (sets `TX_GUARD` and centres the grid).**
   `cd recryst && sbatch -A perc -p a100-40gb --gpus-per-node=2 --ntasks-per-node=2 --array=0 submit_ramp.sh` (x0 r1 at
   `HRATE` 0.2 K/ps to `TMAX`; ≈ 28 h at 444, so it chains two jobs from `ramp.<T>K.restart`, written every 50 K).
   Needs the `ramp_resume` case of `tests/recryst_logic` to pass first. `TMAX` must stay below the
   superheated melting point from the melt-quench. Then `bash scripts/analyze_ramps.sh`. **Read:** whether and where x0
   crystallizes (Tx_xfrac). Set `TX_GUARD` to a Tx measured at a heating rate comparable to the anneals' 10 K/ps
   heat, or to `TMAX` if none exists (nozbl_paw: 900 = `TMAX`). The slow-ramp Tx is not the guard. If nothing crystallizes by
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

## phases: Allegro vs DFT-MD in the DFT cells (`phases/`)
Independent of the other studies; needs only steps A–B. `phases/params/<MODEL_ID>.sh` is a copy of nozbl_paw's
(every value comes from the DFT reference). Method: `phases/README.md`.
1. **DoSPT, once per checkout:** `bash analysis/build_dospt.sh`, then `bash analysis/build_dospt.sh check`.
   **Pass:** the example's total DOS reproduced (nozbl_paw: max difference 1.6e-20).
2. **Pilot:** `cd phases && sbatch --array=9,21 submit.sh` (am_c10 r1, hex_c1 r1; ~1.5 min each on an A30).
   **Pass:** `phases: <phase> done` in `log.phases`; T near 300 K and the conserved energy flat in `thermo.dat`; no
   lost atoms or errors.
3. **Production:** `sbatch --array=0-8,10-20,22-23 submit.sh`, and the relaxation check of the amorphous cells,
   `sbatch --array=0-11 --export=ALL,EQ_PS=25,TAG=eq25 submit.sh`.
4. **Analysis:** `sbatch submit_analysis.sh` (all finished runs, the checks, then `compare`; ~25 min).
   **Pass:** the exact-velocity VDOS overlap ≈ 1.000 for the `EXACT_V` runs and `dft-check` ADF overlap ≈ 1 with
   angles/frame ratio 1.000 (`slurm-analysis-*.out`). If only `compare` fails, rerun it alone:
   `env/cgst-ana/bin/python analysis/phases_compare.py compare --model-id <MODEL_ID>` (from the repository root).
5. **Write-up:** `phases/results/<MODEL_ID>/RESULTS.md`: the metrics per phase against DFT and the other current potential (nozbl_paw ↔ zbl_paw),
   and the relaxation effect.

## What carries over, and what does not
- Carries over: the inputs, scripts, analysis code and their tests; the Q4 criterion *form* (Ge/Sb/Te only); the
  10–60% v_growth window (a geometric result); the 1/√n error estimates.
- Remeasured for every model: everything in each study's `params/<MODEL_ID>.sh` and `calib_params.sh`, plus the timestep, the
  throughput, and the glass-vs-crystal density relation.

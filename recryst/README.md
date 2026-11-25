# Recrystallization (`recryst/`)

This README describes the method. Runs go to `runs/<MODEL_ID>/`, outputs to `results/<MODEL_ID>/`, calibration to
`calib/<MODEL_ID>/`; every model-specific number comes from `recryst/params/<MODEL_ID>.sh` (and the `calib_params.sh` it
sources). The order of steps for a new model, with pass criteria, is `../RUNBOOK.md`; numbers quoted below are nequip_no_zbl's,
as examples, not settings.

Starts from the melt-quench glasses (`meltquench/runs/<MODEL_ID>/<cell>_q<QRATE>_r<rep>/amorphous_300K.data`). All runs are
NPT at 0 bar with the barostat `BARO` (params; see Barostat) and the same damping as the melt-quench. The steps run in this
order, because each one sets parameters for the next.

**Glass vs crystal density.** For nequip_no_zbl the glass is as dense as its crystal (6.239 vs 6.224 g/cc,
`tests/results/nequip_no_zbl/RESULTS.md`), so crystallization barely changes the volume, where in experiment it shrinks
the cell. Check this for every model. `recryst_summary.py`'s Tx_rho is sign-agnostic (max |dρ/dt|), with `drho_x` giving the sign.
Report Tx from the crystalline fraction and the enthalpy release, with Tx_rho as a cross-check.

## 1. Crystallinity criterion (`calib/`)
**Definition.** An atom is crystalline when it has at least `q_nmin` crystal-like bonds. A bond i–j (|r_ij| < `q_rc`)
is crystal-like when the normalized Steinhardt q4 vectors of i and j have a dot product above `q_thr`. This follows
ten Wolde's scheme, with l = 4, which suits the octahedral rocksalt environment. LAMMPS evaluates it on the fly
(`common/in.analysis` and the per-atom `c_ncb` dump column), and `analysis/bondorder.py` reproduces it exactly
(max |Δncb| = 0 against LAMMPS on the smoke dumps). Crystalline clusters are computed from the dumps
(`recryst_summary.py --clusters`) from anneal dumps every 2 ps, fine enough for the first-passage times the MFPT
analysis needs.

**What is counted: Ge/Sb/Te only (`xfracGST`).** Everything in recryst (Tx, the halt level, incubation, clusters,
the calibration) uses `xfracGST`, the crystalline fraction of the Ge/Sb/Te atoms; the `.dat` files also keep
`xfrac` over all atoms. C does not mark crystallinity reliably: in the minimized x10 rocksalt, with C on lattice
sites, far fewer C atoms than Ge/Sb/Te count as crystalline, and in the glass C gives more false positives. A growing crystal is also expected to reject much of the C. Counted over all atoms, the
crystalline ceiling would fall with C content, and any fixed threshold would be reached later in C-rich samples:
a bias in the same direction as the expected effect of C.

**Calibration.**
1. `calib/submit.sh` samples 20 ps of each reference state at 300/500/550/600/650/700 K (54 short jobs):
   - rocksalt crystals x0, x1, x2p5, x5 (x10 rocksalt is unstable and is excluded);
   - the amorphous samples of every composition.
2. `calib/calibrate.py` (`sbatch submit_calibrate.sh` from `calib/`, in the `cgst-ana` env) scans `q_rc` 3.4–4.0 Å, `q_thr` 0.3–0.8 and `q_nmin` 3–7. It picks the criterion that
   maximizes (lowest crystal fraction in any crystal reference − highest crystal fraction in any amorphous reference).
   It prints the suggested anneal `XSTOP` (one per temperature) and `--x-crystal` (per composition) for each reference temperature, including the anneal
   grid 500–700 K, and writes `calib_scan.csv` and
   `calib.png`: (a) each reference's crystalline fraction under the chosen and the
   default criterion; (b) the per-atom crystal-like bond count, crystal vs amorphous references, with the threshold;
   (c) the margin over `q_thr` × `q_nmin`, to show whether the optimum is a plateau or a sharp edge. It warns when
   the best value lies on the edge of the scanned grid; extend the grid then. (On the logic-test references, a
   600 K crystal and a fast-quenched glass, the optimum was at the edge, `q_nmin` 3.) When the best criterion is not
   meaningfully better than a nearby one, `--choose q_rc q_thr q_nmin` (on the grid; checked before the scan) reports
   everything above and the plot for that criterion instead, after the scan's own best line
   (`sbatch --export=ALL,CALIB_ARGS="--choose 3.8 0.6 4" submit_calibrate.sh`).
3. `submit_calibrate.sh` then runs `calib/make_params.py`, which copies the chosen (or best) criterion and its
   per-T tables from `calibrate.out` into `calib/<MODEL_ID>/calib_params.sh`. Rerun `submit_calibrate.sh` with
   `CALIB_ARGS="--choose ..."` to change the choice; nothing else needs editing.
4. For the amorphous references, `calibrate.py` also finds the largest crystalline Ge/Sb/Te cluster in every frame,
   under the chosen and the default criterion, and prints per temperature the suggested `--nucleated-size` for
   `recryst_summary.py --clusters`: 2 × the largest glass cluster over all compositions at that T, rounded up to a
   multiple of 10. It is one value per temperature, so every composition is held to the same threshold.

**Crystal-like order already in the glass.** The 10 K/ps glasses are not free of "crystalline" atoms. For
nequip_no_zbl they read `xfracGST` 0.12–0.14 at 300 K (`meltquench/results/nequip_no_zbl/RESULTS.md`), falling with C
to 5% C, and these atoms form clusters: in the calibration's amorphous references the largest holds 33–144 atoms,
depending on composition and T (`calib/nequip_no_zbl/calibrate.out`), far more than the same number of crystalline
atoms placed at random would give. C lowers this baseline, consistent with C frustrating crystal-like order.

So a small nucleation threshold (the earlier default of 50 atoms) would mark every anneal as nucleated at t = 0,
and an MFPT fit from n = 1 would fit the glass, not nucleation. Hence step 4, and the baseline rule for MFPT
(Kinetics, below). Fractions and onsets measured as a rise above each run's own start (`x_a`, Tx, t_inc, t50) are
not affected. **Known limit:** the calibration samples each glass for 10 ps at Ta, but a ns anneal ages the glass,
and its ordered patches may grow before a nucleus forms. Compare each group's `n_base` (below) with
`--nucleated-size` before trusting `t_nuc`.

**Result, per model:** `calib/<MODEL_ID>/calibrate.out`, and `calib/<MODEL_ID>/calib_params.sh` generated from it
(criterion, `--nucleated-size`, crystal and glass `xfracGST` per composition and T). Every recryst script reads the
latter through `recryst/params/<MODEL_ID>.sh`, so no criterion or per-T value is typed into a script. nequip_no_zbl: 3.9 Å,
0.6, 4 (margin 0.716).

## 2. Heating ramp, Tx (`in.ramp`, `submit_ramp.sh`)
| Stage | T (K) | Duration |
|---|---|---|
| fresh velocities | 300 | 10 ps |
| ramp, 50 K segments, `snap_<T>K.data` at each boundary | 300 → `tmax` | (tmax − 300)/hrate ps |

- `HRATE` and `TMAX` from params: 0.2 K/ps and 900 K for nequip_no_zbl, whose x0 crystallizes at 583 K and x5 at
  650 K on that ramp, while x10 does not crystallize below 900 K. Start with x0 r1 (`sbatch --array=0 submit_ramp.sh`); add replicas
  and compositions where needed. The ramp locates where crystallization is fast, to centre the anneal grid; it is not
  the Ta guard (`TX_GUARD`, below). MD rates are about 10¹⁰ times faster than DSC, so only the **trend of Tx with C
  content** compares with experiment.
- 0.2 K/ps to 900 K takes 3,010 ps (≈ 28 h at 444 on 2 A100s), longer than one job, so `in.ramp` writes
  `ramp.<T>K.restart` at every 50 K boundary and `submit_ramp.sh` chains jobs like `submit_anneal.sh` (resume from the
  newest restart, `MAXCHAIN` default 3, stop on no progress). A killed job loses at most one segment (250 ps at
  0.2 K/ps). `ramp.dat` and `stress.dat` are appended across jobs; each resumed job dumps its own
  `traj.<first step>.lammpstrj.gz`.
- `tmax` must stay below the model's superheated melting point (nequip_no_zbl: Tm_app 1139 K for x0, 983 K for x10, on the 10 K/ps heat). A complete ramp
  writes `ramp_done.txt` last.
- The trajectory is dumped every 5 K; `stress.dat` records the pressure tensor every 1 ps (see Barostat).
- `analysis/recryst_summary.py` reports three estimates of Tx: the T where `xfracGST` has made half its rise from
  the 300 K value to its peak (`Tx_xfrac`; NaN if it rose by less than 0.2, i.e. no crystallization), the peak of
  enthalpy release, and the fastest density change (either sign; `drho_x` gives it). Tx_H and Tx_rho always
  return a value; read them only when Tx_xfrac is finite. The half-rise definition follows each sample's own
  ceiling, so a lower crystalline ceiling does not move Tx.
- Tx vs C content with error bars: the script prints, per composition (replica group), the mean ± sample std over
  the 3 replicas.

## 3. Isothermal anneal (`in.anneal`, `submit_anneal.sh`)
| Stage | T (K) | Duration |
|---|---|---|
| fresh velocities | 300 | 10 ps |
| heat | 300 → Ta | (Ta−300)/10 ps |
| hold | Ta | up to `MAX_NS` (params: 2 ns for nequip_no_zbl); `fix halt` once xfracGST > `XSTOP` (params) |

**Temperature grid and replicas.** The goal is the growth velocity `v_growth` as a function of Ta for each
composition, homogeneous recrystallization (nuclei form during the anneal): v(Ta) should peak, falling at low Ta
(slow atoms) and toward the melting point (small driving force). So the anneals run on a grid of temperatures
rather than at one Ta. The grid `TAS` must be calibration temperatures (each has `--nucleated-size`, crystal and
glass references in `calib_params.sh`; 500–700 K in 50 K steps for nequip_no_zbl), and every Ta must lie below
`TX_GUARD` − 25 K: a Tx at a heating rate comparable to the anneal's 10 K/ps heat (nequip_no_zbl: none measured, so `TMAX`, 900 K). The per-run check that the heat did not crystallize the sample is `analyze_grid.sh`'s TOO HOT verdict.
Homogeneous runs give `v_growth` only where a nucleus forms within the `MAX_NS` hold; a missing point means "no
nucleus", not v = 0.
1. **Phase A, x0** (`CELLS=x0 scripts/submit_grid.sh`, then `scripts/analyze_grid.sh`): `NREP` replicas per Ta. Shows
   where x0 nucleates within `MAX_NS`, and checks `XSTOP`, `X_END` and the barostat on real runs before the grid grows.
2. **Phase B, all compositions** (`scripts/submit_grid.sh` with every cell; Phase A's x0 runs are reused) over the Ta
   where nucleation happens. Per-run `v_growth` and its distribution per composition and Ta are the result
   (`growth_table.csv`). Start with 3 replicas and add more where the spread hides a trend.

**Homogeneous vs seeded v(Ta).** The goal is homogeneous recrystallization. Its weakness is coverage: v(Ta) exists only
where a nucleus forms within the hold, so the high-Ta side of the peak (rare nucleation near Tm) and the low-Ta tail
may be empty, and the peak can fall outside the measurable window. Seeded (heterogeneous) slabs grow a planar front
from a crystal seed at any Ta up to Tm, with no waiting time, so they give the whole v(Ta) curve, including v → 0 at
the model's Tm. The plan is therefore: homogeneous runs for nucleation, t_inc/t50 and v where a nucleus forms;
seeded slabs (x0, x1, x2p5; x5 and x10 have no stable crystal) for the full curve and its peak. If the homogeneous
window turns out narrow for the new model, the seeded slabs become the primary v(Ta) measurement. Compare the two by
trend: a faceted grain's equivalent-sphere radius is not a planar front's position. Seeded inputs are not written yet
(`RUNBOOK.md`, recryst step 5).

Replicas: replica r starts from melt-quench glass ((r − 1) mod 3) + 1 with its own velocities, so 3 replicas use the
3 glasses once each. Nucleation itself is a rare event (one waiting time per run, rate error about 1/√n, 58% for 3
runs); rates from these runs are by-products with that error, not the target.

**Halt level and the crystalline end point.** A perfect x0 crystal reads ≈ 0.95 at 600 K under the final criterion,
but a crystal grown in an anneal (grain boundaries, defects) reads much less: nequip_no_zbl's Phase A x0 runs level
off at `xfracGST` ≈ 0.65–0.67 at 550–700 K (0.55–0.56, still rising, after 2 ns at 500 K). `calibrate.py`'s suggested
halt level, 0.85 × the lowest crystal-reference `xfracGST` (0.72–0.74 at 500–600 K), sits above that plateau, so runs
halting there would keep going for the rest of the hold after crystallizing. Hence **`XSTOP` comes from the grown crystal's plateau in Phase A, not from
the perfect-crystal reference**: set it below that plateau in `recryst/params/<MODEL_ID>.sh` (0.65 for nequip_no_zbl), one value
for every Ta. `analyze_grid.sh` accepts one `XSTOP` per set, ≥ `X_END`.
The normalized fraction X = (xfracGST − x_a)/(x_c − x_a) needs an end point x_c. `recryst_summary.py` picks, first
that applies: `--x-end` (one value for every run); the run's own plateau; `--x-crystal` (the composition's crystal
reference at Ta, from `calibrate.py`); the run's `XSTOP`; `x_c_from` says which. Without `--x-end`, runs of one set
can mix sources (a plateau in some, the ≈ 0.95 crystal reference in others), so t50 would mean a different `xfracGST`
in different runs. **The analysis scripts therefore pass `--x-end` with the composition's `X_END`** (params: `X_END`, or
`X_END_CELL[<cell>]` where a composition never reaches it): t_inc and t50 are measured toward the same `xfracGST` in every run
of a composition, at every Ta. For nequip_no_zbl 0.65 for x0–x5 (each reaches the 0.65 halt at some Ta) and 0.40 for x10,
which does not level off within 2 ns at any Ta; x10's t50 therefore refers to a lower `xfracGST` and is not comparable
across compositions. `v_growth` does not use x_c. (`--x-end` and `--x-crystal` are alternatives; passing both is refused.) x10 has no crystal reference (its
rocksalt disorders), which `--x-end` sidesteps.

**Outputs.**
- `anneal.dat` every 1 ps;
- `hold_start.txt`, the time the hold started and the criterion of the dumped `c_ncb` (fresh start only);
- `stress.dat`, the pressure tensor every 1 ps from the start of the hold;
- the trajectory every 2 ps (one file per job), with image flags (`ix iy iz`, continuous across resumes) so
  unwrapped positions give diffusion over the whole hold;
- `lmp_inputs/log.anneal.<job>/`: reference copy of the input and includes, the command and the provenance of each
  job of the chain (`common/record_inputs.sh`; the same for ramps, `lmp_inputs/log.ramp[.<job>]/`);
- restart files every 50 ps; `submit_anneal.sh` deletes all but the newest two before each job, and all but the
  newest once the run is done (about 6.4 MB each at 444; kept, they would total about 260 MB per 2 ns run).

`recryst_summary.py` reports, per run and as replica mean ± sample std:
- baseline `xfracGST` (x_a), x_c and its source;
- t_inc and t50, where X first exceeds 0.05 and 0.5;
- `n_JMAK`, `k_JMAK`: a description of the curve's shape only. JMAK assumes many nuclei in an unbounded volume; this
  cell usually crystallizes from one nucleus that grows until it meets its own periodic images, so n is not an
  Avrami mechanism exponent and should not be compared across compositions as one;
- the deviatoric stress at the start and at the end of the hold, and their difference in standard errors
  (`sdev_base`, `sdev_end`, `sdev_z`; see Barostat).

Only complete runs are analysed: an anneal needs `anneal_done.txt` and a ramp `ramp_done.txt` (`snap_900K.data` for
ramps from before `tmax`). Others (still
running, or a chain that ran out of `MAXCHAIN`) are listed as incomplete and skipped.

**Kinetics (`--clusters`).** Per dumped frame (`clusters_q<rc>_<thr>_<nmin>.txt`): the largest crystalline
Ge/Sb/Te cluster and the number of such clusters of at least `--nucleus-min` atoms (default 10). From these, per run:
- `t_nuc`, the first hold time the largest cluster reaches `--nucleated-size` atoms. This option is required with
  `--clusters`: use the value `calibrate.py` suggests for Ta and the same criterion (Calibration, step 4);
- `v_growth`, the growth velocity (m/s): the slope of the largest cluster's equivalent-sphere radius while it holds
  10–25% of the Ge/Sb/Te atoms (`V_WINDOW`), i.e. early growth. Grown crystals saturate (nequip_no_zbl: xfracGST
  ≈ 0.65, ≈ 0.61 of the Ge/Sb/Te atoms in the largest cluster) and the front slows throughout a run, so a window
  reaching toward saturation averages in the slow end: the earlier 10–60% window read 2–4× below 10–25% in the
  nequip_no_zbl grid and put slow cells at ≈ 1 m/s whatever their carbon content. Geometry is no limit below 60%
  (a sphere counted exactly in a periodic cell keeps its slope within 0.5%, −5% at 80%; `tests/recryst_logic`).
  The front decelerates even within 10–25%, so v_growth is an early-growth velocity, not a steady state. A faceted grain's equivalent radius is not its facet distance, so
  homogeneous and seeded (planar-front) velocities are compared by trend, not one-to-one;
- `single_grain`: the fraction of that window's frames in which no second cluster has `--nucleated-size` atoms
  (1: one grain throughout). Below 0.8 (a second grain in over 20% of the frames) the radius mixes grains and
  `v_growth` is an upper bound. It is a fraction so that a short-lived second cluster in a frame or two does not mark a run as
  multi-grain.

**Interface velocity: v_flux, not v_growth.** In multi-grain runs (nearly all homogeneous runs: 54 of 57 in the
nequip_no_zbl grid), the largest Q4 cluster grows mostly by swallowing neighbouring grains. Its `v_growth` is then a
coalescence rate, 3-20x the interface velocity, and its apparent peak in Ta tracks the nucleus count. The interface velocity comes from grain
tracking, for the rocksalt compositions (x0-x2p5) only. `analysis/grains.py` per run (Te-sublattice PTM + OVITO
grain segmentation, as a Slurm job), then `analysis/plot_grains.py` gives `v_flux`: the growth of all tracked grains
(merge-corrected) / (n_Te x grain area), up to xfracGST 0.45. A budget check (`budget_flux` ~0.7-0.9 vs
`budget_cluster` 3-7) and the single-grain run (x0 700 K r3: both methods agree) back this choice; see
`results/nequip_no_zbl/RESULTS.md` section 2. For x5/x10 (no segmentable grains) compare t_nuc and t50 only.

Per (composition, Ta) group, two nucleation rates:
- `J_surv`, from the `t_nuc` of all replicas, runs that never nucleated counting as censored at their end (the
  maximum-likelihood rate of an exponential waiting time), with relative error 1/√(runs that nucleated);
- the mean-first-passage-time (MFPT) rate and critical size n* (Wedekind et al., J. Chem. Phys. 126, 134103, 2007):
  the mean over replicas of the first time the largest cluster reaches n, fitted with an error function whose
  midpoint is n*. Only sizes above `n_base`, the largest cluster any replica has in the first 20 ps of its hold
  (the glass's own order), are fitted. n*, τ_J and J are NaN when the fitted n* is not above `n_base` (the critical
  size is then hidden in the glass's own order) or not below the largest size every replica reached.

With 2 ps frames they are estimates with errors of about 1/√(replicas): ~58% at 3, ~30% at 10. Not converged rates.

**Comparing rates (`analysis/rate_compare.py`).** Reads the `--clusters` output of each composition (one file per
composition) and, from each run's `t_nuc` and `t_end`, prints:
- per composition pair, the rate ratio with an approximate 95% interval and an equal-rate test (binomial, given the
  events and exposure × volume of each), with p also Bonferroni-corrected over the pairs;
- per composition, one permutation test of equal rates across the three source glasses (replica r comes from glass
  ((r − 1) mod 3) + 1). If it rejects, the rates depend on the glass and more melt-quench samples are needed.

It has been checked on synthetic data only: a true 4× ratio came out 3.5× with the interval containing 4. With equal
rates, about 6% of pairwise tests and 4.5% of glass tests fell below p = 0.05. A glass test that treated each glass's
exposure as fixed gave 12%, because with 3–4 runs per glass the exposure depends on when the runs nucleate, hence the
permutation test. The glass test is weak: with 10 runs, a glass that nucleates 6× slower is detected about 36% of
the time, so p > 0.05 does not show that the glasses agree.

**Criterion dependence.** n*, t_nuc and Tx depend on where the order parameter puts the crystal/glass boundary: a
strict criterion undercounts the interface atoms of a small embryo. `--clusters` requires the criterion explicitly;
the scripts pass the calibrated one (`Q_ARGS`). For a sensitivity check, rerun under another criterion (each writes its
own `clusters_q…` file); its `--nucleated-size` must come from `calibrate.py` for that criterion. When
the criterion matches the run's own (`hold_start.txt`), the dumped `c_ncb` is used instead of recomputing q4. For Tx,
the `.dat` value uses the run's criterion only; `Tx_H` is criterion-free and is the cross-check.

**Continuation.** A hold can be longer than one wall-time window (nequip_no_zbl: 2 ns at 444 on 2 A100s, about 19 h, within
one; slower GPUs or longer holds need more). Each array task queues its own `afterany` continuation (at most `MAXCHAIN`, default 4). The
continuation resumes from the newest restart file and appends to `anneal.dat` and `stress.dat`, or exits at once if
`anneal_done.txt` exists. It inherits the job's account, partition, QoS, node constraint and GPU layout, so a chain
started on the perc A100s, or on alta's k-nodes, stays there. A continuation that finds no newer restart than its predecessor started from stops the chain
with an error (the predecessor made no progress, e.g. a bad input) instead of queueing more doomed jobs.
- Restart files carry the thermostat and barostat state.
- They do not carry the MSD reference, so the MSD columns restart from zero in each job. Crystallinity is unaffected.

**Barostat (`BARO` in params).** A crystal growing in an orientation the cubic box resists builds deviatoric stress
that persists after growth and could slow its own growth. `stress.dat` records the tensor. `recryst_summary.py`
averages the components over 10 ps blocks (so thermal noise does not add a positive bias) and compares the deviatoric
stress of the last blocks with the first: `sdev_base`, `sdev_end`, and `sdev_z`, their difference in standard errors.
The workflow defaults to `BARO=aniso`, which lets the box relieve that stress; nequip_no_zbl's 12
crystallized Phase A x0 runs (aniso) still end with `sdev_z` 1.6–17.5, with no visible effect on t50. Whether iso and
aniso give the same t_inc, t50 and v_growth has not been checked for the current potentials. Keep `baro` the same within one continuation chain and within everything
that is compared. `TAG` (`RUNTAG` in params) gives a variant its own directories
(`runs/<MODEL_ID>/anneal_<cell>_<TAG>_T<Ta>_r<rep>`) with the same seeds and glasses, so an iso set can sit beside the aniso one. On synthetic production-level noise, `tests/recryst_logic` gives z = −0.9 for
pure noise and z = 16 for a 2 kbar deviatoric step.

## Running
The steps, with their checks, are wrapped in `scripts/` (`scripts/README.md`); the order for a new model is
`../RUNBOOK.md`. Every setting comes from `recryst/params/<MODEL_ID>.sh`. The underlying commands:
```
cd recryst
(cd calib && sbatch --array=0-53 submit.sh)                     # references -> calib/<MODEL_ID>/
(cd calib && sbatch submit_calibrate.sh)                        # calibrate.out, calib_params.sh
sbatch -A perc -p a100-40gb --gpus-per-node=2 --ntasks-per-node=2 --array=0 submit_ramp.sh   # x0 r1, chains itself
bash scripts/analyze_ramps.sh
CELLS=x0 bash scripts/submit_grid.sh --dry-run                  # Phase A; then without --dry-run
bash scripts/analyze_grid.sh summary; bash scripts/analyze_grid.sh verdict
bash scripts/submit_grid.sh --dry-run                           # Phase B: every composition
python ../analysis/rate_compare.py results/<MODEL_ID>/grid_*_T600_clusters.txt   # rates across compositions at one Ta
```
`submit_anneal.sh` maps array index i to (cell `(x0 x1 x2p5 x5 x10)[i / NREP]`, replica `i % NREP + 1`), as
`meltquench/submit.sh` does for NREP 3. The timestep is `DT` from `common/model.sh` (override with
`--export=ALL,DT=...`). Settings read from params can be overridden per submission with `--export=ALL,NAME=value`:
`HRATE` (ramp); `XSTOP`, `MAX_NS` (anneal); also `TA` (required), `NREP`, `MAXCHAIN` (default 4 for anneals, 3 for ramps) and `EXTRA_VARS`
(further LAMMPS `-var` options; the criterion and barostat are always passed from params).

## Validation
**`tests/recryst_logic`: PASS** (nequip_no_zbl: job 12359106, 46 checks; `check.py` writes
`RESULT.txt`). On the 1×1×1 x0 glass (461 atoms) from `tests/mq_logic`, dt 1 fs:
- **Ramp** (10 K/ps): exit 0; `snap_350K` … `snap_900K`; T follows the programmed schedule (mean deviation +1.2 K);
  `stress.dat` has a row for every `ramp.dat` step.
- **Ramp restart** (`ramp_resume`): a ramp stopped at 600 K resumes to 900 K, and a resume after the last restart is
  read as complete; `ramp.dat` and `stress.dat` continue with no gap; restarts every 50 K; each resumed job dumps
  its own trajectory file.
- **Anneal with resume** (tscale 0.1): both jobs exit 0; the hold ends at the programmed step 24000; `anneal.dat`
  (0–24000) and `stress.dat` (4000–24000) continue across the resume with no gap; restarts every 5000 steps;
  trajectory frames every 2 ps, the two jobs' files overlapping at 10000–14000 and agreeing there in unwrapped
  position (to 5e-11 Å), with no atom moving more than 3.7 Å between frames across the resume (image flags carried
  over); `hold_start.txt` = 4 ps and `xstop` are read back by the summary.
- **`fix halt`** (xstop 0.0, `baro aniso`): stops at its first check, step 5000; the hold ran anisotropic.
- **Continuation:** `sbatch --test-only` accepts `submit_anneal.sh` with the inherited resource flags. The chain's
  stop-on-no-progress rule was checked separately with stubbed Slurm and LAMMPS: a failing first job stops the chain
  at the second link; a progressing chain continues. Restart pruning was checked the same way over a four-job
  chain: each job starts with the newest two restart files, the finished run keeps only the newest, every job exits
  0. `TAG` was checked the same way: `submit_anneal.sh` and `submit_ramp.sh` give a tagged task its own directory
  (`anneal_x0_aniso_T600_r1`, `ramp_x1_aniso_h1_r1`) with the untagged task's seed and glass and the `EXTRA_VARS`
  options; the tagged run starts although the untagged one is done, the untagged run still reports done, a tagged
  continuation finds its own directory, and the continuation inherits `TAG` and `EXTRA_VARS`. Without `TAG` the
  directory names are unchanged. `sbatch --test-only` accepts tagged submissions of both scripts.
- **Ge/Sb/Te-only crystallinity, with C present** (`in.calib` on the 512-atom x10 glass at 300 K and the minimized
  1×1×1 x5 rocksalt at 600 K): on every dumped frame LAMMPS's `xfracGST` and `xfrac` equal a recount from the dump
  over Ge/Sb/Te and over all atoms (difference 0 atoms), and the two differ; `calibrate.py` runs on these references
  and reports `xfracGST`, a suggested `XSTOP`, and a suggested `--nucleated-size` equal to 2 × the largest glass
  cluster recounted from the dump.
- **Analysis:** `recryst_summary.py` runs on the outputs and skips an incomplete anneal by name; `hold_start.txt`
  records the criterion; `--clusters` without `--nucleated-size` or without the criterion exits with an error, and with
  both prints the group's nucleation line with `n_base`; the `#` header names MODEL_ID, the model the run's log names
  and the criterion, with a WARNING line for a run of another model; clusters from the dumped `c_ncb` equal clusters from a recount, with each overlapping
  frame counted once. (Both copies of an overlapping frame are identical on one node, so the test cannot tell which
  file a repeated frame was taken from; the later-wins rule for `.dat` rows is a known answer below.)
- **Known answers:** `load_dat` keeps the last row of a repeated step; the half-rise `Tx_xfrac` of a synthetic
  ramp is 650 K for both a 0.8 and a 0.6 ceiling (a fixed 0.5 threshold would give 654 K and 665 K); `v_growth`
  recovers 200 m/s for a growing sphere, also counted exactly in a periodic cell (within 3% with the `V_WINDOW` window,
  180 m/s if it ran to 90%); `single_grain` is the exact fraction of window frames without a second grain (1, 0, 0.5)
  and NaN without a window; `J_surv` matches the censored-exponential formula; `smooth()` keeps a
  constant constant; the stress statistic gives |z| < 5 on production-level noise
  and z = 16 for a 2 kbar deviatoric step; the MFPT fit recovers n* = 40 and τ_J = 500 ps, recovers n* = 140 on top of a 100-atom glass baseline, and
  gives NaN when n* = 40 lies below that baseline. `rate_compare.py`: it parses `recryst_summary.py`'s run rows and
  nucleation line and recovers the cell volume from `J_surv`; equal events at a quarter of the exposure give a rate
  ratio of exactly 4 with the exact binomial p and its Bonferroni correction; the glass permutation test gives p = 1
  for identical glasses and about 2/120 (the exact permutation count) when one glass's 3 runs never nucleate.

**Defects this test has caught (all fixed):** LAMMPS `if` cannot compare filenames (now a numeric `resume` flag);
Gilbreth rejects `sbatch` without a memory request (a flaw in the test's own continuation check); a single
instantaneous temperature of a 461-atom cell is too noisy to check a ramp (now checked against the whole schedule).
A synthetic pre-test also showed the first stress statistic could not separate a 2 kbar step from noise (z 5.1 vs
3.8), so it was replaced by the end-versus-start comparison.

## Budget
Measured throughput (`tests/scaling`), nequip_no_zbl (`tests/scaling/submit_size.sh`, x10): 3.12 ns/day at 333 on 1 A100;
at 444 (32.8k atoms) 1.34 ns/day on 1 A100 (34.3 of 41 GB GPU memory) and 2.59 on 2 (1.93×, 23.3 GB
each), hence `NGPU` = 2 per 444 run.
- Calibration: 54 jobs × 20 ps (references at the melt-quench `SIZE`), minutes each.
- Ramp: 0.2 K/ps to 900 K is 3,010 ps: ≈ 28 h at 444 on 2 A100s, i.e. two chained jobs.
- Anneals (nequip_no_zbl, 444, `MAX_NS` 2, 2 A100s): a hold that never halts is ≈ 19 h, one job. The full grid (5
  compositions × 5 Ta × 3 replicas) is 75 runs ≈ 2,900 GPU-hours if nothing halts, about 12 days on 10 perc GPUs (5
  runs at a time), about 3.5 days on alta's 36 (18 at a time, when free); `fix halt` cuts this where runs crystallize, and Phase A decides where Phase B is worth running.
  Nucleation exposure per run (volume × time) is 2.37 × 2 ns ≈ 4.7 ns of a 333 cell.
- Disk (gzipped dumps, about 0.25 MB per 13.8k-atom frame, ≈ 0.6 MB at 444): up to 1,000 frames ≈ 0.6 GB per 2 ns run,
  ≈ 45 GB for the grid. All on `/scratch` (200 TB quota).

GPUs: strachan's A30 cap is 6 GPUs shared with other members, often only 2 free, so 1–3 two-GPU jobs at a time.
perc adds 10 A100-40GB, so 5 two-GPU jobs; alta 36 A100-80GB (k-nodes, `--constraint=K`), so up to 18. **Every
submission is a separate go-ahead.**

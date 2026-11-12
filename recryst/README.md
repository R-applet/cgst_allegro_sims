# Part 3: Recrystallization

Starts from the 10 K/ps melt-quench samples (`meltquench/runs/<cell>_q10_r<rep>/amorphous_300K.data`). All runs are
NPT at 0 bar, isotropic unless rerun anisotropic (see Barostat), with the same damping as Part 2. The steps run in
this order, because each one sets parameters for the next.

**Reference limitation.** The starting glasses are slightly denser than the model's own crystal, as in its DFT
reference (`meltquench/README.md`; `tests/RESULTS.md` 1g, 1k), so crystallization expands the cell: the opposite
sign to experiment. `recryst_summary.py`'s Tx_rho is therefore sign-agnostic (max |dρ/dt|), with `drho_x` giving
the sign. Report Tx from the crystalline fraction and the enthalpy release, with Tx_rho as a cross-check, and treat
the crystallization strain and its effect on the kinetics as an artefact of the DFT reference.

## 1. Crystallinity criterion (`calib/`)
**Definition.** An atom is crystalline when it has at least `q_nmin` crystal-like bonds. A bond i–j (|r_ij| < `q_rc`)
is crystal-like when the normalized Steinhardt q4 vectors of i and j have a dot product above `q_thr`. This follows
ten Wolde's scheme, with l = 4, which suits the octahedral rocksalt environment. LAMMPS evaluates it on the fly
(`common/in.analysis` and the per-atom `c_ncb` dump column), and `analysis/bondorder.py` reproduces it exactly
(max |Δncb| = 0 against LAMMPS on the smoke dumps). Crystalline clusters are computed from the dumps
(`recryst_summary.py --clusters`) from anneal dumps every 2 ps, fine enough for the first-passage times the MFPT
analysis needs.

**What is counted: Ge/Sb/Te only (`xfracGST`).** Everything in Part 3 (Tx, the halt level, incubation, clusters,
the calibration) uses `xfracGST`, the crystalline fraction of the Ge/Sb/Te atoms; the `.dat` files also keep
`xfrac` over all atoms. C does not mark crystallinity reliably: in the minimized x10 rocksalt, with C on lattice
sites, 55% of C atoms count as crystalline against 98% of Ge/Sb/Te, and in the x10 glass C gives more false
positives (14% vs 9%). A growing crystal is also expected to reject much of the C. Counted over all atoms, the
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
3. The chosen values are recorded here and passed to the production runs
   (`EXTRA_VARS="-var q_rc .. -var q_thr .. -var q_nmin .."`) only if they differ from the defaults (3.6, 0.5, 4).
4. For the amorphous references, `calibrate.py` also finds the largest crystalline Ge/Sb/Te cluster in every frame,
   under the chosen and the default criterion, and prints per temperature the suggested `--nucleated-size` for
   `recryst_summary.py --clusters`: 2 × the largest glass cluster over all compositions at that T, rounded up to a
   multiple of 10. It is one value per temperature, so every composition is held to the same threshold.

**Crystal-like order already in the glass.** The 10 K/ps glasses are not free of "crystalline" atoms. Measured on
the first eight production glasses (x0, x1, x2p5; final 50 ps at 300 K; default criterion):
- `xfracGST` is 0.13–0.16, against 0.015 in the 1500 K liquid of the same runs. The stricter logic-test optimum
  (3.7, 0.7, 3) still gives 0.09–0.12.
- These atoms form clusters: the largest holds 83–314 atoms (up to 9 clusters of ≥ 50 per frame), against 13–15
  for the same number of crystalline atoms placed at random.
- The ordered regions persist: about 60% of the atoms in ≥ 50-atom clusters are still crystalline 140 ps later,
  against about 14% by chance. How they connect changes from frame to frame, so the largest cluster is not the same
  set of atoms over time. At 300 K they do not grow: `xfracGST` creeps from 0.144 to 0.155 over 140 ps.
- C lowers the baseline (x0 > x1 > x2p5), consistent with C frustrating crystal-like order.

So a small nucleation threshold (the earlier default of 50 atoms) would mark every anneal as nucleated at t = 0,
and an MFPT fit from n = 1 would fit the glass, not nucleation. Hence step 4, and the baseline rule for MFPT
(Kinetics, below). Fractions and onsets measured as a rise above each run's own start (`x_a`, Tx, t_inc, t50) are
not affected. (Measured with one-off scripts on the dumps of `meltquench/runs`, not kept; step 4 reproduces the
cluster sizes at each calibration temperature.) **Known limit:** the calibration samples each glass for 10 ps at
Ta, but a ns anneal ages the glass, and its ordered patches may grow before a nucleus forms. Compare each group's
`n_base` (below) with `--nucleated-size` before trusting `t_nuc`.

**Result: `q_rc` 3.8 Å, `q_thr` 0.6, `q_nmin` 4** (calibration jobs 12295527 and 12308622; `calib/calibrate.out`
from `--choose 3.8 0.6 4`, job 12309345). Pass it to every Part 3 run as
`EXTRA_VARS="-var q_rc 3.8 -var q_thr 0.6 -var q_nmin 4"` and to the analysis as `--q-rc 3.8 --q-thr 0.6 --q-nmin 4`.
- The best margin rises with `q_rc` and flattens: 0.682 / 0.702 / 0.711 / 0.712 / 0.705 at 3.6 / 3.7 / 3.8 / 3.9 /
  4.0 Å, with `q_thr` 0.6 and `q_nmin` 4 best at every `q_rc` from 3.5 Å. The strict optimum, 3.9 Å, beats 3.8 Å by
  0.0009, which is noise. 3.8 Å was kept: it stays further from the second-neighbour shell (about 4.2 Å), and the
  1 K/ps and 0.2 K/ps ramps had already been submitted with it.
- Against the default (3.6, 0.5, 4), the lowest crystal reference barely moves (0.805 vs 0.812, x5 at 700 K) and the
  glasses drop from at most 0.151 to at most 0.094. The gain is all on the glass side.
- In `calib.png` (b), crystal atoms mostly have 5–7 crystal-like bonds and glass atoms 0–2; the cut at 4 falls
  between them. In (c), the neighbouring `q_thr`/`q_nmin` cells give 0.65–0.69, so the choice is not sensitive.

| T (K) | `XSTOP` | `--x-crystal` x0 / x1 / x2p5 / x5 | glass `xfracGST` max | `--nucleated-size` |
|---|---|---|---|---|
| 300 | 0.78 | 0.947 / 0.963 / 0.949 / 0.922 | 0.094 | 190 |
| 500 | 0.75 | 0.950 / 0.960 / 0.934 / 0.877 | 0.086 | 230 |
| 550 | 0.73 | 0.951 / 0.956 / 0.923 / 0.862 | 0.090 | 250 |
| 600 | 0.72 | 0.950 / 0.951 / 0.916 / 0.842 | 0.076 | 260 |
| 650 | 0.70 | 0.948 / 0.947 / 0.904 / 0.822 | 0.064 | 210 |
| 700 | 0.68 | 0.947 / 0.941 / 0.898 / 0.805 | 0.051 | 130 |

x10 has no crystal reference: its runs take x_c from their plateau, else `XSTOP`. The largest glass cluster at each temperature under
this criterion is 63–130 atoms (300–700 K), against 103–269 under the default.

## 2. Heating ramp, Tx (`in.ramp`, `submit_ramp.sh`)
| Stage | T (K) | Duration |
|---|---|---|
| fresh velocities | 300 | 10 ps |
| ramp, 50 K segments, `snap_<T>K.data` at each boundary | 300 → 900 | 600 ps at 1 K/ps |

- 3 replicas per composition, one per melt-quench sample.
- A 0.2 K/ps rate check on x0 r1 shows how far Tx shifts with heating rate. MD rates are about 10¹⁰ times faster
  than DSC, so only the **trend of Tx with C content** compares with experiment, not its absolute value.
  It takes 3,010 ps: about 21.6 h on 2 A30s, but 23–25 h on one A100-40GB (2.9–3.1 ns/day), past the 24 h limit,
  and `in.ramp` has no restart. Run it on the A30s.
- 900 K stays below the model's superheated melting point (about 1090 K at 2 K/ps).
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
| hold | Ta | up to 5 ns; `fix halt` once xfracGST > `XSTOP` (default 0.8) |

**Temperature grid and replicas.** The goal is the growth velocity `v_growth` as a function of Ta for each
composition, homogeneous recrystallization (nuclei form during the anneal): v(Ta) should peak, falling at low Ta
(slow atoms) and toward the melting point (small driving force). So the anneals run on a grid of temperatures
rather than at one Ta. The grid is the calibrated range, 500–700 K in 50 K steps: each Ta has its `XSTOP`,
per-composition `--x-crystal` and `--nucleated-size` from `calib/calibrate.out`. Every Ta must lie below a Tx
measured at a heating rate no faster than the anneal's 10 K/ps; the 1 K/ps ramps do not crystallize below 900 K, so
all five qualify (`RESULTS.md` sections 2–4). Homogeneous runs give `v_growth` only where a nucleus forms within the
5 ns hold; a missing point means "no nucleus", not v = 0. Seeded (heterogeneous) slabs, planned separately, cover
the Ta outside that window.
1. **Phase A, x0** (`scripts/submit_screen.sh`, `scripts/analyze_screen.sh`): 3 replicas per Ta. First iso/aniso
   pairs at 600 and 650 K (`TAS="600 650"`, with and without `BARO=aniso`): the 0.2 K/ps x0 crystal built 5 kbar of
   deviatoric stress (`sdev_z` 91), so the barostat is settled before the rest of the grid. Then 500, 550 and 700 K
   with the chosen barostat. This also shows where x0 nucleates within 5 ns.
2. **Phase B, all compositions** over the Ta where Phase A (and the C cells' own runs) nucleate, 3 replicas each,
   reusing the Phase A x0 runs; per-run `v_growth` and its distribution per composition and Ta are the result.
   Start with 3 replicas and add more where the spread hides a trend.

Replicas: replica r starts from melt-quench glass ((r − 1) mod 3) + 1 with its own velocities, so 3 replicas use the
3 glasses once each. Nucleation itself is a rare event (one waiting time per run, rate error about 1/√n, 58% for 3
runs); rates from these runs are by-products with that error, not the target.

**Halt level and the crystalline end point.** A perfect x0 crystal reads ≈ 0.93 at 600 K under the default
criterion, and a crystal grown in an anneal (grain boundaries, defects) reads less, so a halt at 0.9 would rarely
fire. `XSTOP` (default 0.8, on `xfracGST`) should be set below what a crystallized sample reads at Ta: `calibrate.py`
prints a suggestion per reference temperature (0.85 × the lowest crystal-reference `xfracGST`). The normalized
fraction X = (xfracGST − x_a)/(x_c − x_a) uses x_c, the fully crystalline value: the run's own plateau if it reached
one, else `--x-crystal` (the composition's own crystal-reference value at Ta, printed per composition by
`calibrate.py`), else the run's `XSTOP`; `x_c_from` says which. `--x-crystal` takes one value per call, so run
`recryst_summary.py` once per composition. Using the lowest reference (x5) for all would overstate X for x0, whose
crystal reads about 0.95 against x5's 0.84 at 600 K. x10 has no crystal reference (its rocksalt disorders), so it
falls back to its plateau or `XSTOP`.

**Outputs.**
- `anneal.dat` every 1 ps;
- `hold_start.txt`, the time the hold started and the criterion of the dumped `c_ncb` (fresh start only);
- `stress.dat`, the pressure tensor every 1 ps from the start of the hold;
- the trajectory every 2 ps (one file per job), with image flags (`ix iy iz`, continuous across resumes) so
  unwrapped positions give diffusion over the whole hold;
- restart files every 50 ps; `submit_anneal.sh` deletes all but the newest two before each job, and all but the
  newest once the run is done (about 2.6 MB each; kept, they would total about 260 MB per 5 ns run).

`recryst_summary.py` reports, per run and as replica mean ± sample std:
- baseline `xfracGST` (x_a), x_c and its source;
- t_inc and t50, where X first exceeds 0.05 and 0.5;
- `n_JMAK`, `k_JMAK`: a description of the curve's shape only. JMAK assumes many nuclei in an unbounded volume; this
  cell usually crystallizes from one nucleus that grows until it meets its own periodic images, so n is not an
  Avrami mechanism exponent and should not be compared across compositions as one;
- the deviatoric stress at the start and at the end of the hold, and their difference in standard errors
  (`sdev_base`, `sdev_end`, `sdev_z`; see Barostat).

Only complete runs are analysed: an anneal needs `anneal_done.txt` and a ramp `snap_900K.data`. Others (still
running, or a chain that ran out of `MAXCHAIN`) are listed as incomplete and skipped.

**Kinetics (`--clusters`).** Per dumped frame (`clusters_q<rc>_<thr>_<nmin>.txt`): the largest crystalline
Ge/Sb/Te cluster and the number of such clusters of at least `--nucleus-min` atoms (default 10). From these, per run:
- `t_nuc`, the first hold time the largest cluster reaches `--nucleated-size` atoms. This option is required with
  `--clusters`: use the value `calibrate.py` suggests for Ta and the same criterion (Calibration, step 4);
- `v_growth`, the growth velocity (m/s): the slope of the largest cluster's equivalent-sphere radius while it holds
  10–60% of the Ge/Sb/Te atoms. A sphere meets its own periodic image at π/6 ≈ 52% of the cell, but counted
  exactly in a periodic cell its slope stays within 0.5% of the true one up to 60% (−1.5% at 70%, −5% at 80%;
  `tests/recryst_logic`), so 60% is the cap. A faceted grain's equivalent radius is not its facet distance, so
  homogeneous and seeded (planar-front) velocities are compared by trend, not one-to-one;
- `single_grain`: 1 if no second cluster reaches `--nucleated-size` during that window, 0 if one does (the radius
  then mixes grains; at low Ta, where many nuclei form, check this before trusting v_growth).

Per (composition, Ta) group, two nucleation rates:
- `J_surv`, from the `t_nuc` of all replicas, runs that never nucleated counting as censored at their end (the
  maximum-likelihood rate of an exponential waiting time), with relative error 1/√(runs that nucleated);
- the mean-first-passage-time (MFPT) rate and critical size n* (Wedekind et al., J. Chem. Phys. 126, 134103, 2007):
  the mean over replicas of the first time the largest cluster reaches n, fitted with an error function whose
  midpoint is n*. Only sizes above `n_base`, the largest cluster any replica has in the first 20 ps of its hold
  (the glass's own order), are fitted. n*, τ_J and J are NaN when the fitted n* is not above `n_base` (the critical
  size is then hidden in the glass's own order) or not below the largest size every replica reached.

These are the kinetics to compare across compositions. With 2 ps frames and 10 replicas they are estimates with
roughly 30% errors, not converged rates.

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
strict criterion undercounts the interface atoms of a small embryo. Run the kinetics under both the default and
the calibrated criterion (`--q-rc --q-thr --q-nmin`; each writes its own `clusters_q…` file) and report both. When
the criterion matches the run's own (`hold_start.txt`), the dumped `c_ncb` is used instead of recomputing q4. For Tx,
the `.dat` value uses the run's criterion only; `Tx_H` is criterion-free and is the cross-check.

**Continuation.** A 5 ns hold of a 13k-atom cell takes about 1.5 days on 2 A30s (3.35 ns/day), which is longer than
one wall-time window. Each array task queues its own `afterany` continuation (at most `MAXCHAIN`, default 4). The
continuation resumes from the newest restart file and appends to `anneal.dat` and `stress.dat`, or exits at once if
`anneal_done.txt` exists. It inherits the job's account, partition, QoS and GPU layout, so a chain started on the
perc A100s stays there. A continuation that finds no newer restart than its predecessor started from stops the chain
with an error (the predecessor made no progress, e.g. a bad input) instead of queueing more doomed jobs.
- Restart files carry the thermostat and barostat state.
- They do not carry the MSD reference, so the MSD columns restart from zero in each job. Crystallinity is unaffected.

**Barostat.** All runs use isotropic NPT (`baro iso`). A crystal growing in an orientation the cubic box resists
would build deviatoric stress that persists after growth, and could slow its own growth. `stress.dat` records the
tensor. `recryst_summary.py` averages the components over 10 ps blocks (so thermal noise does not add a positive
bias) and compares the deviatoric stress of the last blocks with the first: `sdev_base`, `sdev_end`, and `sdev_z`,
their difference in standard errors. If `sdev_z` > 5 in a run that crystallized, rerun that (composition, Ta) with
`EXTRA_VARS="-var baro aniso"` and `TAG=aniso`, and compare t50. `TAG` gives the reruns their own directories
(`runs/anneal_<cell>_aniso_T<Ta>_r<rep>`, so the finished iso runs are not mistaken for done) with the same seeds and
glasses, and the summary treats them as their own replica group. Rerun the whole replica set of that composition, so
both barostats have the same number of runs. On synthetic production-level noise, `tests/recryst_logic` (one
seed) gives z = −0.9 for pure noise and z = 16 for a 2 kbar deviatoric step; five seeds tried while choosing the
statistic gave |z| ≤ 1.3 and 11–21. Keep `baro` the same within one continuation chain.

## Running
The steps after calibration, with their checks and the final criterion built in, are wrapped in `scripts/`
(`scripts/README.md` lists them in order). The underlying commands:
```
cd recryst
sbatch --array=0-14 submit_ramp.sh                              # 1 K/ps, 5 cells x 3 replicas
sbatch --array=0 --export=ALL,HRATE=0.2 submit_ramp.sh          # 0.2 K/ps, x0 r1
sbatch --array=0-2 --export=ALL,TA=600 submit_anneal.sh         # screening: x0 replicas at 600 K (scripts/submit_screen.sh
                                                                  # wraps this with its checks, BARO=aniso for the pairs)
sbatch --array=0-49 --export=ALL,TA=600,NREP=10 submit_anneal.sh # production: 10 replicas of every cell
# anneals on one perc A100-40GB per job (continuations stay on perc; keep the 0.2 K/ps ramp on the A30s):
sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --array=0-2 --export=ALL,TA=600 submit_anneal.sh
# anisotropic rerun of x1's 10 replicas (Barostat), into runs/anneal_x1_aniso_T600_r*:
EXTRA_VARS="-var baro aniso" sbatch --array=10-19 --export=ALL,TA=600,NREP=10,TAG=aniso submit_anneal.sh
python ../analysis/recryst_summary.py runs/*                      # ramps and anneals; anneals at one Ta, one
                                                                  # composition: --x-crystal from calibrate.py
python ../analysis/recryst_summary.py --clusters --nucleated-size N runs/anneal_*_T600_*   # t_nuc, v_growth, rates;
                                                                  # N from calibrate.py at Ta, same criterion
python ../analysis/recryst_summary.py --clusters --nucleated-size N --q-rc .. --q-thr .. --q-nmin .. runs/anneal_*_T600_*
python ../analysis/rate_compare.py prod_*_clusters.txt           # one --clusters output per composition
```
The array index → (cell, replica) mapping is the same as in `meltquench/submit.sh`. The timestep comes from
`common/defaults.sh` (shared with the melt-quench; override with `--export=ALL,DT=...`). Other settings, passed with
`--export=ALL,NAME=value`: `HRATE` (ramp, K/ps, default 1); `TA` (anneal, required), `NREP` (replicas per cell,
default 3), `MAX_NS` (hold length, default 5), `XSTOP` (halt level on `xfracGST`, default 0.8), `MAXCHAIN` (jobs per
chain, default 4); `EXTRA_VARS` (extra LAMMPS `-var`
options for either, e.g. the calibrated criterion or `-var baro aniso`).

## Validation
**`tests/recryst_logic`: PASS** (job 12290193; `check.py` writes `RESULT.txt`; after the nucleation-threshold
change, `calibrate.py` and `check.py` were rerun on that job's outputs, since no LAMMPS input changed; 37 checks since the `rate_compare.py` known answers, 39 since the periodic-cell `v_growth` and `single_grain` checks). On the 1×1×1 x0 glass (461 atoms)
from `tests/mq_logic`, dt 1 fs:
- **Ramp** (10 K/ps): exit 0; `snap_350K` … `snap_900K`; T follows the programmed schedule (mean deviation +1.2 K);
  `stress.dat` has a row for every `ramp.dat` step.
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
  records the criterion; `--clusters` without `--nucleated-size` exits with an error, and with it prints the group's
  nucleation line with `n_base`; clusters from the dumped `c_ncb` equal clusters from a recount, with each overlapping
  frame counted once. (Both copies of an overlapping frame are identical on one node, so the test cannot tell which
  file a repeated frame was taken from; the later-wins rule for `.dat` rows is a known answer below.)
- **Known answers:** `load_dat` keeps the last row of a repeated step; the half-rise `Tx_xfrac` of a synthetic
  ramp is 650 K for both a 0.8 and a 0.6 ceiling (a fixed 0.5 threshold would give 654 K and 665 K); `v_growth`
  recovers 200 m/s for a growing sphere, also counted exactly in a periodic cell (199 m/s with the 10–60% window,
  180 m/s if it ran to 90%); `single_grain` is 1, 0 or NaN as a second nucleus is absent, present or there is no
  window; `J_surv` matches the censored-exponential formula; `smooth()` keeps a
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
Measured throughput at 13.8k atoms (`tests/RESULTS.md`, 1d): 3.35 ns/day per 2-A30 job, about 3.0 ns/day per
1-A100 job.
- Ramps: 15 runs × 610 ps ≈ 4.4 h each.
- Anneals: screening 9 runs, production 50 runs (`NREP=10`), each up to ≈ 5 ns ≈ 36 h in the worst case: about
  2,100 job-hours, against about 1,600 for the earlier plan of 3 replicas at 3 temperatures for every composition.
  `fix halt` should cut this a lot, provided `XSTOP` is set below the crystallized `xfracGST` (see Halt level); a
  shorter `MAX_NS` with more replicas also works, since runs that do not nucleate still count (censored) in `J_surv`.
- Calibration: 54 jobs × 20 ps, roughly 15–20 min each on one A30 (estimated from the 2-A30 throughput).
- Disk (gzipped dumps, about 0.25 MB per 13.8k-atom frame): anneals up to 2,500 frames ≈ 0.7 GB per 5 ns run,
  about 40 GB for the plan above; ramps about 30 MB per run. All on `/scratch` (200 TB quota).

GPUs: strachan's A30 cap is 6 GPUs shared with other members, often only 2 free, so 1–3 two-GPU jobs at a time.
perc adds 10 A100-40GB, so up to 10 one-GPU jobs. **Review checkpoint before scaling the anneals.**

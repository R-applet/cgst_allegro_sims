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
2. `calib/calibrate.py` scans `q_rc` 3.4–3.8 Å, `q_thr` 0.3–0.8 and `q_nmin` 3–7. It picks the criterion that
   maximizes (lowest crystal fraction in any crystal reference − highest crystal fraction in any amorphous reference).
   It prints the suggested anneal `XSTOP` and `--x-crystal` for each reference temperature, including the anneal
   temperatures 550/600/650 K, and writes `calib_scan.csv` and
   `calib.png`: (a) each reference's crystalline fraction under the chosen and the
   default criterion; (b) the per-atom crystal-like bond count, crystal vs amorphous references, with the threshold;
   (c) the margin over `q_thr` × `q_nmin`, to show whether the optimum is a plateau or a sharp edge. It warns when
   the best value lies on the edge of the scanned grid; extend the grid then. (On the logic-test references, a
   600 K crystal and a fast-quenched glass, the optimum was at the edge, `q_nmin` 3.)
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

**Result:** _pending (needs the Part 2 amorphous samples)_.

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

**Choosing Ta, and how many replicas.** Nucleation in a 13.8k-atom cell is a rare, single event: each run gives one
waiting time, close to exponentially distributed, so a rate from n runs has a relative error of about 1/√n (58% for
3 runs). Composition effects smaller than a factor of two in the rate would be invisible with 3 replicas. Hence:
1. **Screening:** x0 at 550/600/650 K (below the x0 Tx from step 2), 3 replicas each, to find the Ta where x0
   nucleates inside 5 ns but not within the heating.
2. **Production:** every composition at that one Ta with `NREP=10` (`sbatch --array=0-49 --export=ALL,TA=..,NREP=10
   submit_anneal.sh`), about 30% error per rate; 20 replicas for the compositions being compared most closely.
   Replica r starts from melt-quench glass ((r − 1) mod 3) + 1 with its own velocities: beyond 3 replicas the
   glasses are reused, so replicas of one glass share its structure (pre-existing subcritical order) and differ only
   in their dynamics. If the rates turn out to differ between glasses, more melt-quench samples are needed.

**Halt level and the crystalline end point.** A perfect x0 crystal reads ≈ 0.93 at 600 K under the default
criterion, and a crystal grown in an anneal (grain boundaries, defects) reads less, so a halt at 0.9 would rarely
fire. `XSTOP` (default 0.8, on `xfracGST`) should be set below what a crystallized sample reads at Ta: `calibrate.py`
prints a suggestion per reference temperature (0.85 × the lowest crystal-reference `xfracGST`). The normalized
fraction X = (xfracGST − x_a)/(x_c − x_a) uses x_c, the fully crystalline value: the run's own plateau if it reached
one, else `--x-crystal` (the crystal-reference value at Ta, also printed by `calibrate.py`), else the run's `XSTOP`;
`x_c_from` says which.

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
  10–60% of the Ge/Sb/Te atoms.

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
`EXTRA_VARS="-var baro aniso"` and compare t50. On synthetic production-level noise, `tests/recryst_logic` (one
seed) gives z = −0.9 for pure noise and z = 16 for a 2 kbar deviatoric step; five seeds tried while choosing the
statistic gave |z| ≤ 1.3 and 11–21. Keep `baro` the same within one continuation chain.

## Running
```
cd recryst
sbatch --array=0-14 submit_ramp.sh                              # 1 K/ps, 5 cells x 3 replicas
sbatch --array=0 --export=ALL,HRATE=0.2 submit_ramp.sh          # 0.2 K/ps, x0 r1
sbatch --array=0-2 --export=ALL,TA=600 submit_anneal.sh         # screening: x0 replicas at 600 K
sbatch --array=0-49 --export=ALL,TA=600,NREP=10 submit_anneal.sh # production: 10 replicas of every cell
# anneals on one perc A100-40GB per job (continuations stay on perc; keep the 0.2 K/ps ramp on the A30s):
sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --array=0-2 --export=ALL,TA=600 submit_anneal.sh
python ../analysis/recryst_summary.py runs/*                      # ramps and anneals; anneals at one Ta:
                                                                  # --x-crystal from calibrate.py
python ../analysis/recryst_summary.py --clusters --nucleated-size N runs/anneal_*_T600_*   # t_nuc, v_growth, rates;
                                                                  # N from calibrate.py at Ta, same criterion
python ../analysis/recryst_summary.py --clusters --nucleated-size N --q-rc .. --q-thr .. --q-nmin .. runs/anneal_*_T600_*
```
The array index → (cell, replica) mapping is the same as in `meltquench/submit.sh`. The timestep comes from
`common/defaults.sh` (shared with the melt-quench; override with `--export=ALL,DT=...`). Other settings, passed with
`--export=ALL,NAME=value`: `HRATE` (ramp, K/ps, default 1); `TA` (anneal, required), `NREP` (replicas per cell,
default 3), `MAX_NS` (hold length, default 5), `XSTOP` (halt level on `xfracGST`, default 0.8), `MAXCHAIN` (jobs per
chain, default 4); `EXTRA_VARS` (extra LAMMPS `-var`
options for either, e.g. the calibrated criterion or `-var baro aniso`).

## Validation
**`tests/recryst_logic`: PASS** (job 12290193; `check.py` writes `RESULT.txt`; after the nucleation-threshold
change, `calibrate.py` and `check.py` were rerun on that job's outputs, 34 checks, since no LAMMPS input changed). On the 1×1×1 x0 glass (461 atoms)
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
  0.
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
  recovers 200 m/s for a growing sphere; `J_surv` matches the censored-exponential formula; `smooth()` keeps a
  constant constant; the stress statistic gives |z| < 5 on production-level noise
  and z = 16 for a 2 kbar deviatoric step; the MFPT fit recovers n* = 40 and τ_J = 500 ps, recovers n* = 140 on top of a 100-atom glass baseline, and
  gives NaN when n* = 40 lies below that baseline.

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

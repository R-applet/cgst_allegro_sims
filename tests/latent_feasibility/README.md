# Feasibility: Allegro latent features vs Q4 for crystallinity

Exploratory, not a recryst gate. Question: do the model's per-atom latents separate crystal from glass, compared
with the Q4 criterion, and do they transfer across composition?

## What was run (2026-11-06)
1. `analysis/latent_features.py` (in the container, CPU, about 6 min for 19 frames of 461–512 atoms) produced
   `features.npz`.
   - Per atom: the 256-D invariant scalar edge features after the single Allegro layer (`edge_features`, 256x0e),
     mean-pooled over the atom's edges; the per-atom energy E_i; and the Q4 crystal-like bond count.
   - Check: the sum of E_i matches the model's total energy, and it matches LAMMPS's PE on the same dumped
     configuration (x0, step 0: −112.59 eV both).
2. `analyze.py` scored the descriptors and wrote `RESULT.txt`.

**Data:**
- `smoke_x0` / `smoke_x10`: copies of the smoke dumps.
- `mqlogic_x0`: a copy of the `tests/mq_logic` x0 trajectory.

**References** (Ge/Sb/Te atoms, all at ~520–690 K):
- crystal: x0 rocksalt at 600 K (smoke) and the mq_logic heating ramp at 615/689 K;
- glass: the mq_logic x0 quench at 678/601/~520 K. This glass was quenched in about 12 ps, so it is very
  disordered and an easy case.

The train/test split is by frame.

## Results (`RESULT.txt`)

| per-species ROC AUC, held-out frames | Ge | Sb | Te |
|---|---|---|---|
| Q4 bond count | 0.999 | 0.994 | 0.980 |
| E_i (per-atom energy) | 0.558 | 0.534 | 0.899 |
| latent, linear probe (Fisher LDA) | 0.998 | 1.000 | 1.000 |
| latent, unsupervised (PCA + 2-means accuracy) | 0.688 | 0.788 | 0.572 |

| test frames, Ge/Sb/Te | crystalline fraction, Q4 | crystalline fraction, latent |
|---|---|---|
| x0 crystal | 0.931 | 0.996 |
| x0 glass | 0.037 | 0.015 |

| x10 (x0-trained classifiers) | step 0 | 1500 | 3000 |
|---|---|---|---|
| Q4 | 0.976 | 0.774 | 0.620 |
| latent | 0.720 | 0.488 | 0.345 |
| per-atom agreement | 0.744 | 0.709 | 0.707 |

## Reading
- **In distribution (x0 at ~600 K), the latent separates the phases at least as well as Q4.** It does better on the
  atoms Q4 struggles with: it labels 99.6% of crystal atoms crystalline against Q4's 93.1%. Which atoms Q4 misses
  was not checked; neighbours of vacancies are the likely candidates. On this easy, very disordered glass the margin is small; the result is sharper, not
  different.
- **E_i alone is not a crystallinity descriptor** (AUC ≈ 0.55 for Ge/Sb), so the latent adds real information
  beyond the energy.
- **Unsupervised clustering fails** (accuracy 0.57–0.79). The dominant variation in latent space is not the phase,
  so the latent needs labelled references, which the recryst calibration states provide.
- **It does not transfer to x10.** On the just-minimized x10 rocksalt, Q4 says 98% crystalline and the
  x0-trained latent says 72%. That is the composition confound expected a priori: C neighbours move Ge/Sb/Te
  latents out of the x0 crystal distribution. (Step 0 is also a minimized, about 0 K structure, while training was
  at 600 K. That should make it look *more* crystalline, not less.) On the disordering trajectory the two
  disagree on about 30% of atoms. These data cannot say which is right, because x10 has no stable crystal reference.

## Limits
- 512-atom cells; one very fast-quenched glass.
- Train and test frames come from the same trajectories, so they are correlated.
- A 256-D linear probe on about 2,000 training atoms (with shrinkage) could still overfit. The held-out frames show
  no sign of it, but this set cannot rule it out.

## If pursued
- Rerun with the recryst calibration references (all compositions, 300–700 K, real 10 K/ps glasses).
- Train per composition, and report a train-on-x / test-on-y transfer matrix next to Q4.
- Compare both descriptors on the anneal trajectories (xfrac(t), first detection of a growing nucleus,
  per-atom disagreement maps).
- x10 needs its own crystal reference, or must be left out of latent-based labelling.

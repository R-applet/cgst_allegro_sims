# Feasibility: Allegro latent features vs Q4 for crystallinity

Exploratory, not a recryst gate. Question: do the model's per-atom latents separate crystal from glass, compared
with the Q4 criterion, and do they transfer across composition?

## Method (first run 2026-11-06 with an earlier potential; not yet run with the current ones)
1. `analysis/latent_features.py` (in the container, CPU, about 6 min for 19 frames of 461–512 atoms) writes
   `features.npz`.
   - Per atom: the 256-D invariant scalar edge features after the single Allegro layer (`edge_features`, 256x0e),
     mean-pooled over the atom's edges; the per-atom energy E_i; and the Q4 crystal-like bond count.
   - Check: the sum of E_i must match the model's total energy and LAMMPS's PE on the same dumped configuration.
2. `analyze.py` scores the descriptors (per-species ROC AUC of Q4, E_i, a linear probe and an unsupervised split on
   held-out frames; transfer of x0-trained classifiers to x10) and writes `RESULT.txt`.

**Data:**
- `smoke_x0` / `smoke_x10`: copies of the smoke dumps.
- `mqlogic_x0`: a copy of the `tests/mq_logic` x0 trajectory.

**References** (Ge/Sb/Te atoms, all at ~520–690 K):
- crystal: x0 rocksalt at 600 K (smoke) and the mq_logic heating ramp at 615/689 K;
- glass: the mq_logic x0 quench at 678/601/~520 K. This glass was quenched in about 12 ps, so it is very
  disordered and an easy case.

The train/test split is by frame.

## If pursued
- Rerun with the recryst calibration references (all compositions, 300–700 K, real 10 K/ps glasses).
- Train per composition, and report a train-on-x / test-on-y transfer matrix next to Q4.
- Compare both descriptors on the anneal trajectories (xfrac(t), first detection of a growing nucleus,
  per-atom disagreement maps).
- x10 needs its own crystal reference, or must be left out of latent-based labelling.

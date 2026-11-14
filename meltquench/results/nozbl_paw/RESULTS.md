# Melt-quench results: nozbl_paw

Method: `meltquench/README.md`. Settings: `meltquench/params/nozbl_paw.sh` (4×4×4 cells, 29.5k–32.8k atoms; melt
1500 K, 100 ps hold, 10 K/ps quench; 2 A100s per run). Runs in `meltquench/runs/nozbl_paw/`, each with its input
record in `lmp_inputs/log.mq/`.

**Status (2026-11-13 22:20):** superheating pilot done and passed (x0 r1, x10 r1); the other 13 production runs
submitted (job array 12363504). The full table per composition follows when they finish.

## Superheating pilot (job 12359216; x0 r1 and x10 r1, also production runs)

`mq_summary_pilot.txt` (`analysis/mq_summary.py`); run5_ep301's same runs (3×3×3) in brackets:

| run | Tm_app (K) | ρ liquid, 1500 K | ρ glass, 300 K | Tg (K) | xfracGST 300 K | closest pair, liquid / glass |
|---|---|---|---|---|---|---|
| x0 r1 | 1139 (1130) | 5.471 (5.525) | 6.239 (6.292) | 790 (835) | 0.144 (0.149) | Ge–Ge 2.06 / 2.30 Å |
| x10 r1 | 983 (1025) | 5.388 (5.444) | 6.094 (6.146) | 760 (880) | 0.173 (0.202) | C–C 1.08 / 1.16 Å (1.10 / 1.18) |

Pass criteria (`RUNBOOK.md`, meltquench step 1), all met:
- MSD gate: smallest per-species MSD in the hold 651 Å² (x0) and 354 Å² (x10), gate 100 Å²;
- 1500 K is 361 K above the higher Tm_app (≥ ~300 K required), so TMELT stays 1500 K and HOLD_PS 100 ps;
- no close contacts without ZBL: every pair ≥ 1.0 Å. Per pair the x10 liquid minima are within 0.10 Å of run5_ep301's;
  closer than run5_ep301 only for Te–C (1.72 vs 1.80 Å), C–C (1.08 vs 1.10 Å) and Ge–Sb / Sb–Te (0.02–0.04 Å);
- no errors or lost atoms in either log (only the known Kokkos sorting warnings).

x0's Slurm state is FAILED (exit 2) although the simulation completed (all stages, outputs and `Total wall time`):
`common/run_lmp.sh` was edited while the job was inside LAMMPS, and bash failed reading the changed file afterwards.
Fixed in commit 855a40f (`exec srun`); the run is used as is.

**Densities.** Both glasses are ~0.9% less dense than run5_ep301's, and the liquids ~1% less dense. The x0 glass
(6.239 g/cc) is as dense as this potential's rocksalt crystal (6.224 g/cc at 3×3×3, `tests/density`): the glass is
not lighter than the crystal, unlike experiment (6–7% lighter), but no longer denser as for run5_ep301.
`tests/dft_glass` on this x0 glass: **CONSISTENT**, density +0.01% vs DFT's own cold melt-quenched glass (run5_ep301:
+0.85%), largest coordination difference 0.14 (Z_Sb 3.80 vs 3.93; criterion 0.15).

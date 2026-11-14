# Melt-quench results: nozbl_paw

Method: `meltquench/README.md`. Settings: `meltquench/params/nozbl_paw.sh` (4×4×4 cells, 29.5k–32.8k atoms; melt
1500 K, 100 ps hold, 10 K/ps quench; 2 A100s per run). Runs in `meltquench/runs/nozbl_paw/`, each with its input
record in `lmp_inputs/log.mq/`.

**Status (2026-11-14):** done. All 15 runs (5 compositions × 3 replicas at 10 K/ps; pilot job 12359216, production
job array 12363504, 3.6–4.9 h each on 2 A100s) passed the MSD gate, with no errors. Analysis: `mq_summary.txt`
(`analysis/mq_summary.py`), `mq_structure.txt` and the per-group `.dat` tables (`analysis/mq_structure.py`, job
12375697). run5_ep301's values (3×3×3, same protocol) in brackets.

## Properties against C content (mean ± sample std, 3 replicas)

| C (at.%) | ρ liquid, 1500 K (g/cc) | ρ glass, 300 K (g/cc) | Tm_app (K) | Tg (K) | xfracGST, 300 K | MSD gate (Å², min of 3) |
|---|---|---|---|---|---|---|
| 0 | 5.472 ± 0.001 (5.524) | 6.239 ± 0.002 (6.289) | 1139 ± 5 (1129) | 765 ± 22 (807) | 0.142 ± 0.008 (0.155) | 648 |
| 1.07 | 5.470 ± 0.001 (5.524) | 6.231 ± 0.002 (6.277) | 1138 ± 5 (1128) | 802 ± 19 (780) | 0.132 ± 0.001 (0.144) | 419 |
| 2.54 | 5.463 ± 0.001 (5.514) | 6.213 ± 0.002 (6.260) | 1112 ± 3 (1117) | 778 ± 15 (833) | 0.128 ± 0.001 (0.139) | 438 |
| 5.14 | 5.442 ± 0.000 (5.493) | 6.174 ± 0.001 (6.221) | 1069 ± 20 (1077) | 787 ± 10 (757) | 0.123 ± 0.003 (0.133) | 397 |
| 9.96 | 5.388 ± 0.000 (5.444) | 6.094 ± 0.002 (6.148) | 978 ± 5 (984) | 760 ± 5 (815) | 0.129 ± 0.006 (0.143) | 349 |

- **Density falls with C** by the same relative amount as with run5_ep301: −1.5% in the liquid and −2.3% in the glass
  from 0 to 10% C (run5_ep301: −1.4%, −2.2%). Every value sits ~0.9% (liquid ~1%) below run5_ep301's.
- **The apparent melting point** matches run5_ep301 within the replica spread: flat to 1% C, then falling to 978 K at
  10% C. It is a superheating limit on a 10 K/ps ramp, an upper bound on the model's Tm.
- **Tg is not resolved**: 760–802 K with 5–22 K scatter and no trend with C.
- **Crystal-like order** (`xfracGST`, Ge/Sb/Te only, default criterion 3.6/0.5/4, final 50 ps) is ~0.01 lower than
  run5_ep301's at every composition and falls slightly with C to 5%.
- **Closest approach** (`mq_summary.txt`, per pair, liquid / glass): Ge/Sb/Te pairs ≥ 1.98 Å in every liquid; Ge–C
  1.62–1.64 / 1.78–1.84 Å, Te–C 1.72–1.80 / 1.88–1.98 Å, C–C 1.08–1.12 / 1.16–1.20 Å at every C content (run5_ep301
  x10: Ge–C 1.64 / 1.80, Te–C 1.80 / 1.92, C–C 1.10 / 1.18). No close contacts without ZBL.

## Structure of the glass (`mq_structure.txt`, final 50 ps at 300 K)

| C (at.%) | Z_Ge | Z_Sb | Z_Te | Z_C | C bonded to C |
|---|---|---|---|---|---|
| 0 | 4.42 (4.49) | 3.81 (3.86) | 2.99 (3.03) | — | — |
| 1.07 | 4.41 | 3.78 | 2.94 | 3.76 (3.70) | 0.24 (0.30) |
| 2.54 | 4.40 | 3.77 | 2.91 | 3.44 | 0.51 (0.63) |
| 5.14 | 4.39 | 3.75 | 2.88 | 3.19 | 0.70 (0.80) |
| 9.96 | 4.37 (4.43) | 3.72 (3.80) | 2.84 (2.90) | 3.04 (3.02) | 0.86 (0.91) |

(± ≤ 0.01 over replicas for Z_Ge/Sb/Te, ≤ 0.04 for Z_C and the C–C fraction.) Coordination falls with C as with
run5_ep301, each species ~0.05–0.08 lower, consistent with the slightly lighter glass. C clusters at every content,
but less than with run5_ep301 (86% vs 91% of C bonded to C at 10% C). Angles, S(q), C motifs and C-cluster size
distributions: the per-group `.dat` files.

## Superheating pilot (job 12359216; x0 r1 and x10 r1, also production runs)

How `TMELT` and `HOLD_PS` were confirmed before the production runs.

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

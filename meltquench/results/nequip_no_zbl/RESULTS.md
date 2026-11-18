# Melt-quench results: nequip_no_zbl

Method: `meltquench/README.md`. Settings: `meltquench/params/nequip_no_zbl.sh` (4×4×4 cells, 29.5k–32.8k atoms; melt
1500 K, 100 ps hold, 10 K/ps quench; 2 A100s per run). Runs in `meltquench/runs/nequip_no_zbl/`, each with its input
record in `lmp_inputs/log.mq/`.

**Status (2026-11-15):** done, including the 5 and 1 K/ps rate runs (Quench rate, below) and the report
(`report/`). All 15 runs (5 compositions × 3 replicas at 10 K/ps; pilot job 12359216, production
job array 12363504, 3.6–4.9 h each on 2 A100s) passed the MSD gate, with no errors. Analysis: `mq_summary.txt`
(`analysis/mq_summary.py`), `mq_structure.txt` and the per-group `.dat` tables (`analysis/mq_structure.py`, job
12375697).

## Properties against C content (mean ± sample std, 3 replicas)

| C (at.%) | ρ liquid, 1500 K (g/cc) | ρ glass, 300 K (g/cc) | Tm_app (K) | Tg (K) | xfracGST, 300 K | MSD gate (Å², min of 3) |
|---|---|---|---|---|---|---|
| 0 | 5.472 ± 0.001 | 6.239 ± 0.002 | 1139 ± 5 | 765 ± 22 | 0.142 ± 0.008 | 648 |
| 1.07 | 5.470 ± 0.001 | 6.231 ± 0.002 | 1138 ± 5 | 802 ± 19 | 0.132 ± 0.001 | 419 |
| 2.54 | 5.463 ± 0.001 | 6.213 ± 0.002 | 1112 ± 3 | 778 ± 15 | 0.128 ± 0.001 | 438 |
| 5.14 | 5.442 ± 0.000 | 6.174 ± 0.001 | 1069 ± 20 | 787 ± 10 | 0.123 ± 0.003 | 397 |
| 9.96 | 5.388 ± 0.000 | 6.094 ± 0.002 | 978 ± 5 | 760 ± 5 | 0.129 ± 0.006 | 349 |

- **Density falls with C:** −1.5% in the liquid and −2.3% in the glass from 0 to 10% C.
- **The apparent melting point** is flat to 1% C, then falls to 978 K at 10% C. It is a superheating limit on a 10 K/ps ramp, an upper bound on the model's Tm.
- **Tg is not resolved**: 760–802 K with 5–22 K scatter and no trend with C.
- **Crystal-like order** (`xfracGST`, Ge/Sb/Te only, default criterion 3.6/0.5/4, final 50 ps; `xfracGST_a` in
  `mq_summary.txt`) is 0.12–0.14 and falls slightly with C to 5%.
- **Closest approach** (`mq_summary.txt`, per pair, liquid / glass): Ge/Sb/Te pairs ≥ 1.98 Å in every liquid; Ge–C
  1.62–1.64 / 1.78–1.84 Å, Te–C 1.72–1.80 / 1.88–1.98 Å, C–C 1.08–1.12 / 1.16–1.20 Å at every C content. No close contacts without ZBL.

## Structure of the glass (`mq_structure.txt`, final 50 ps at 300 K)

| C (at.%) | Z_Ge | Z_Sb | Z_Te | Z_C | C bonded to C |
|---|---|---|---|---|---|
| 0 | 4.42 | 3.81 | 2.99 | — | — |
| 1.07 | 4.41 | 3.78 | 2.94 | 3.76 | 0.24 |
| 2.54 | 4.40 | 3.77 | 2.91 | 3.44 | 0.51 |
| 5.14 | 4.39 | 3.75 | 2.88 | 3.19 | 0.70 |
| 9.96 | 4.37 | 3.72 | 2.84 | 3.04 | 0.86 |

(± ≤ 0.01 over replicas for Z_Ge/Sb/Te, ≤ 0.04 for Z_C and the C–C fraction.) Coordination of every species falls
with C. C clusters at every content (86% of C bonded to C at 10% C). Angles, S(q), C motifs and C-cluster size
distributions: the per-group `.dat` files.

## Quench rate (x0 and x10, one replica each at 5 and 1 K/ps)

5 K/ps: job array 12384205 on 3 A30s (`NGPU=3`), 5.4 h (x0) and 6.8 h (x10). 1 K/ps: job array 12383793 on 2
A100-80GBs (alta), 11.0 h and 13.5 h. All four passed the MSD gate (≥ 347 Å²), with no errors. Analysis:
`mq_summary_q5.txt`, `mq_summary_rates.txt` (every x0/x10 run), `mq_structure_q5.txt`, `mq_structure_q1.txt` and the
`x0_q5_*`, `x10_q5_*`, `x0_q1_*`, `x10_q1_*` tables (jobs 12388565, 12388566). 10 K/ps: mean ± std of 3 replicas.

| | xfracGST 300 K | ρ glass (g/cc) | Tg (K) | Z_Ge / Z_Sb / Z_Te | C bonded to C (in clusters ≥ 10; largest) |
|---|---|---|---|---|---|
| x0, 10 K/ps | 0.142 ± 0.008 | 6.239 ± 0.002 | 765 ± 22 | 4.42 / 3.81 / 2.99 | — |
| x0, 5 K/ps | 0.159 | 6.239 | 805 | 4.43 / 3.81 / 3.01 | — |
| x0, 1 K/ps | **0.298** | 6.239 | 790 | 4.52 / 3.88 / 3.10 | — |
| x10, 10 K/ps | 0.129 ± 0.006 | 6.094 ± 0.002 | 760 ± 5 | 4.37 / 3.72 / 2.84 | 0.87 (0.53; 69) |
| x10, 5 K/ps | 0.144 | 6.100 | 765 | 4.40 / 3.74 / 2.85 | 0.87 (0.60; 58) |
| x10, 1 K/ps | **0.214** | 6.104 | 775 | 4.42 / 3.80 / 2.93 | 0.94 (0.89; 223) |

- **1 K/ps partially crystallizes the glass:** xfracGST rises during the quench
  below ~650 K (x0 mostly by 450 K), and the x0 slab shows ordered domains (`report/figures/render_crystal_like`).
  Coordination moves toward the octahedral crystal. C slows it: x10 ends lower. Recryst keeps the 10 K/ps glasses.
- **5 K/ps barely changes the glass**: xfracGST +0.015–0.017 (about two replica std, one run each), no ordered domains;
  density and coordination within 0.1% and 0.03.
- Density does not depend on rate (x0 identical; x10 +0.16% at 1 K/ps). Slower quenching coarsens the C network and
  turns C bond angles planar (1 K/ps: 51% between 115 and 130°, vs 44% at 10 K/ps). No close contacts at any rate
  (C–C ≥ 1.10 Å in the liquid).

## Report

`report/`: `meltquench_report.pdf` (from `meltquench_report.tex`) and `meltquench_slides.pptx` (from `build_deck.js`),
with figures from `make_figures.py` and `render_structures.py` (both with `env/cgst-ana`; see each file's header).
They report this potential alone (regenerated 2026-11-18), including the no-ZBL close-contact check and the
bond-cutoff check on its 10% C glasses; the summary slide leaves columns for `nequip_zbl` and `rushik_zbl_pairwise`,
to be filled when those potentials are melt-quenched with the same protocol.

## Superheating pilot (job 12359216; x0 r1 and x10 r1, also production runs)

How `TMELT` and `HOLD_PS` were confirmed before the production runs.

`mq_summary_pilot.txt` (`analysis/mq_summary.py`):

| run | Tm_app (K) | ρ liquid, 1500 K | ρ glass, 300 K | Tg (K) | xfracGST 300 K | closest pair, liquid / glass |
|---|---|---|---|---|---|---|
| x0 r1 | 1139 | 5.471 | 6.239 | 790 | 0.144 | Ge–Ge 2.06 / 2.30 Å |
| x10 r1 | 983 | 5.388 | 6.094 | 760 | 0.173 | C–C 1.08 / 1.16 Å |

Pass criteria (`RUNBOOK.md`, meltquench step 1), all met:
- MSD gate: smallest per-species MSD in the hold 651 Å² (x0) and 354 Å² (x10), gate 100 Å²;
- 1500 K is 361 K above the higher Tm_app (≥ ~300 K required), so TMELT stays 1500 K and HOLD_PS 100 ps;
- no close contacts without ZBL: every pair ≥ 1.0 Å (x10 liquid: C–C 1.08 Å, Ge–C 1.62 Å, Te–C 1.72 Å);
- no errors or lost atoms in either log (only the known Kokkos sorting warnings).

x0's Slurm state is FAILED (exit 2) although the simulation completed (all stages, outputs and `Total wall time`):
`common/run_lmp.sh` was edited while the job was inside LAMMPS, and bash failed reading the changed file afterwards.
Fixed in commit 855a40f (`exec srun`); the run is used as is.

**Densities.** The x0 glass (6.239 g/cc) is as dense as this potential's rocksalt crystal (6.224 g/cc at 3×3×3,
`tests/density`): the glass is not lighter than the crystal, unlike experiment (6–7% lighter).
`tests/dft_glass` on this x0 glass: **CONSISTENT**, density +0.01% vs DFT's own cold melt-quenched glass, largest coordination difference 0.14 (Z_Sb 3.80 vs 3.93; criterion 0.15).

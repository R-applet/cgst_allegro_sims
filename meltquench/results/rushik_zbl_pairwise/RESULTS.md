# Melt-quench results: rushik_zbl_pairwise

Allegro with per-pair ZBL at the edge of the training data (1.15–1.76 Å) (`models/provenance.md`). Method: `meltquench/README.md`. Settings: `meltquench/params/rushik_zbl_pairwise.sh`, the values
of nequip_no_zbl (4×4×4 cells, 29.5k–32.8k atoms; melt 1500 K, 100 ps hold, 10 K/ps quench; 2 A100s per run), the
same seeds. Runs in `meltquench/runs/rushik_zbl_pairwise/`. nequip_no_zbl's values (`../nequip_no_zbl/RESULTS.md`) in parentheses.

**Status (2026-11-19):** the 15 runs at 10 K/ps done (5 compositions × 3 replicas; pilot job 12431657 = x0 r1
and x10 r1, replica 1 job 12432651, replicas 2–3 job 12434153; perc A100-40GB n-nodes, 3.6–6.3 h each). Every run
passed the MSD gate (smallest per-species MSD in the hold ≥ 318 Å², gate 100) with no errors. Analysis:
`mq_summary.txt` (`analysis/mq_summary.py`), `mq_structure.txt` and the per-group `.dat` tables
(`analysis/mq_structure.py`, job 12445194). No 5 or 1 K/ps runs for this model.

## Properties against C content (mean ± sample std, 3 replicas)

| C (at.%) | ρ liquid, 1500 K (g/cc) | ρ glass, 300 K (g/cc) | Tm_app (K) | Tg (K) | xfracGST, 300 K |
|---|---|---|---|---|---|
| 0 | 5.476 ± 0.000 (5.472) | 6.242 ± 0.002 (6.239) | 1138 ± 6 (1139) | 763 ± 24 (765) | 0.142 ± 0.003 (0.142) |
| 1.07 | 5.474 ± 0.001 (5.470) | 6.233 ± 0.003 (6.231) | 1128 ± 2 (1138) | 747 ± 10 (802) | 0.136 ± 0.005 (0.132) |
| 2.54 | 5.464 ± 0.001 (5.463) | 6.215 ± 0.002 (6.213) | 1117 ± 4 (1112) | 737 ± 10 (778) | 0.130 ± 0.002 (0.128) |
| 5.14 | 5.443 ± 0.002 (5.442) | 6.176 ± 0.002 (6.174) | 1073 ± 14 (1069) | 778 ± 23 (787) | 0.125 ± 0.002 (0.123) |
| 9.96 | 5.388 ± 0.001 (5.388) | 6.096 ± 0.004 (6.094) | 977 ± 11 (978) | 758 ± 14 (760) | 0.130 ± 0.007 (0.129) |

- **Glass density** follows nequip_no_zbl's within 0.005 g/cc at every composition (−2.3% from 0 to 10% C).
- **Liquid density at 1500 K** is +0.07% (x0) to +0.00% (x10) from nequip_no_zbl's, against a replica
  scatter of ≤ 0.002 g/cc.
- **Tm_app** is within 11 K of nequip_no_zbl's (largest at x1, 1128 against 1138 K). **Tg** differs by -55 to -2 K, with a replica scatter of up to 24 K: not resolved, as for nequip_no_zbl.
- **Closest approach in the liquid** (`mq_summary.txt`, per pair): C–C 1.13 1.09 1.10 1.09 Å (x1…x10 group means), Ge/Sb/Te pairs ≥ 2.0 Å;
  the same as nequip_no_zbl, so the short-range term changes nothing at the contacts these liquids reach.

## Structure of the glass (`mq_structure.txt`, final 50 ps at 300 K; mean of 3 replicas)

| C (at.%) | Z_Ge | Z_Sb | Z_Te | Z_C | C bonded to C |
|---|---|---|---|---|---|
| 0 | 4.42 (4.42) | 3.82 (3.81) | 2.99 (2.99) | — | — |
| 1.07 | 4.42 (4.41) | 3.80 (3.78) | 2.95 (2.94) | 3.71 (3.76) | 0.29 ± 0.04 (0.24) |
| 2.54 | 4.41 (4.40) | 3.78 (3.77) | 2.92 (2.91) | 3.37 (3.44) | 0.57 ± 0.02 (0.51) |
| 5.14 | 4.40 (4.39) | 3.76 (3.75) | 2.89 (2.88) | 3.13 (3.19) | 0.76 ± 0.02 (0.70) |
| 9.96 | 4.37 (4.37) | 3.73 (3.72) | 2.85 (2.84) | 3.04 (3.04) | 0.88 ± 0.00 (0.87) |

Coordination agrees with nequip_no_zbl's within 0.01–0.02 per species. **C clusters more at intermediate C content:**
0.57 ± 0.02 of C bonded to C at 2.54% C and 0.76 ± 0.02 at 5.14% (nequip_no_zbl
0.51 and 0.70), several replica standard deviations apart, with a correspondingly
lower Z_C; at 1.07% and 9.96% C the potentials agree. Angles, S(q), C motifs and cluster sizes: the per-group `.dat` files.

## Glass vs DFT (`tests/dft_glass`, x0 r1 glass)
**CONSISTENT:** model glass 6.237 g/cc against DFT's coldest-20 melt-quench frames 6.235 (+0.02%), largest
coordination difference 0.11 (criterion 0.15); nequip_no_zbl +0.01%, 0.14
(`tests/results/rushik_zbl_pairwise/dft_glass.txt`).

## Superheating pilot (job 12431657; x0 r1 and x10 r1, also production runs)
`mq_summary_pilot.txt`. TMELT 1500 K and HOLD_PS 100 ps confirmed (`meltquench/params/rushik_zbl_pairwise.sh`): see the params
comments for the pilot's Tm_app, MSD and closest approaches.

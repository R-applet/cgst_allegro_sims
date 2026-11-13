# Part 2 results: run5_ep301

> Since 2026-11-13 the default potential is `nozbl_paw`: to rerun this model's tools or scripts, set
> `MODEL_ID=run5_ep301` (e.g. `MODEL_ID=run5_ep301 bash scripts/analyze_grid.sh ...`).


Melt-quench (`meltquench/README.md`, method) with MODEL_ID run5_ep301, TMELT 1500 K, HOLD_PS 100, 10 K/ps
(`params/run5_ep301.sh`). Runs in `meltquench/runs/run5_ep301/`, summaries here, figures and write-up in `report/`.
State at tag `run5_ep301-final`; paths below that name `meltquench/results` or `meltquench/runs` are now the
`run5_ep301/` subdirectories.

## Production runs (2026-11-10)
Written up with figures in `report/`: `part2_results.md`, `part2_report.pdf` (LaTeX source alongside) and
`part2_slides.pptx`, all rebuilt from `results/` and `runs/` by the scripts there.

17 runs, all past the MSD gate with `hold_ps` = 100: 3 replicas at 10 K/ps for each composition, and one at 1 K/ps
for x0 and x10. `python analysis/mq_summary.py --out meltquench/results meltquench/runs/*_q*_r*` (run before the
per-model move; output now here). Mean ± sample std over the 3 replicas at 10 K/ps:

| x (at.% C) | ρ_liquid, 1500 K (g/cc) | ρ_glass, 300 K (g/cc) | Tm_app (K) | Tg (K) | xfracGST, 300 K |
|---|---|---|---|---|---|
| 0 | 5.524 ± 0.001 | 6.289 ± 0.004 | 1129 ± 2 | 807 ± 26 | 0.155 ± 0.006 |
| 1 | 5.524 ± 0.001 | 6.277 ± 0.003 | 1128 ± 13 | 780 ± 22 | 0.144 ± 0.008 |
| 2.5 | 5.514 ± 0.001 | 6.260 ± 0.001 | 1117 ± 5 | 833 ± 53 | 0.139 ± 0.002 |
| 5 | 5.493 ± 0.000 | 6.221 ± 0.002 | 1077 ± 26 | 757 ± 45 | 0.133 ± 0.009 |
| 10 | 5.444 ± 0.002 | 6.148 ± 0.002 | 984 ± 35 | 815 ± 57 | 0.143 ± 0.010 |

- **Density falls with C**, in the liquid by 1.4% and in the glass by 2.2% from x0 to x10, steadily and well outside
  the replica spread. The x0 glass (6.29) is denser than the model's own crystal (6.24), the reference limitation at
  the top of this file.
- **The apparent melting point falls with C** above 2.5%: 1129 K for x0, 1077 K for x5 and 984 K for x10. It is a
  superheating limit on a 10 K/ps ramp, an upper bound on Tm, and its replica spread grows with C (± 26–35 K).
- **Tg shows no trend.** The bilinear fit scatters by 20–60 K between replicas, more than any difference between
  compositions. A 10 K/ps quench with 3 replicas does not resolve the effect of C on Tg.
- **Crystal-like order in the glass** (`xfracGST`, Ge/Sb/Te atoms, default criterion 3.6/0.5/4) falls slightly with C,
  from 0.155 to 0.133 at x5. x10 reads 0.143, but it is the vacancy-free endpoint, so it differs in more than C. The
  all-atom `xfrac` that `mq_summary.py` prints as `xfrac_a` reads x10 at 0.194, because C atoms add false positives
  (`recryst/README.md`, "What is counted"). Use `xfracGST`.
- **Coordination** at 300 K (cutoffs above): Ge 4.49 → 4.43, Sb 3.86 → 3.80, Te 3.03 → 2.90 from x0 to x10. C is
  3.70-coordinated in x1 and 3.02 in x10. C–C bonds per C rise from 0.34 (x1) to 1.84 (x10): at 10% C most C atoms
  bond to other C. Per Ge atom there are 0.40 C neighbours in x10, against 0.12 per Sb and 0.03 per Te.
- **1 K/ps partially crystallizes.** `xfracGST` at 300 K is 0.28 (x0) and 0.26 (x10), against 0.13–0.16 at 10 K/ps,
  and it rises during the quench: x0 at 1 K/ps goes from 0.12 at 600 K to 0.27 at 400 K, while at 10 K/ps it goes
  from 0.085 to 0.13. So the 1 K/ps runs are partly crystallized glasses, not more relaxed ones, and Part 3 starts
  from the 10 K/ps glasses. Slower quenching also clusters C further: C–C bonds per C 2.32 at 1 K/ps against 1.84.
  Glass density barely moves with rate (x0 6.283 against 6.289; x10 6.151 against 6.148).

**Structure** (`analysis/mq_structure.py --out meltquench/results meltquench/runs/*_q*_r*`, job 12309964, last 50 ps
at 300 K; per-group tables in `meltquench/results/`). Coordination agrees with `mq_summary.py` to ±0.01.
- **C clusters with C content.** The fraction of C atoms bonded to another C rises from 0.30 (x1) through 0.63 (x2p5)
  and 0.80 (x5) to 0.91 (x10). Sizes grow with it: in x1 the largest C cluster has 4 atoms; in x10, 75% of C sits in
  clusters of 10 or more, up to 129 atoms. So at 10% C, carbon forms an extended network inside the glass, not
  dispersed dopant atoms.
- **C motifs.** In x1 the most common C environments are Ge- and Sb-rich (Ge₃Sb 19%, Ge₂C 13%, Ge₂Sb₂ 12%). In x10
  they are C-rich: C₃ 22%, GeC₂ 21%, C₂ 15%.
- **Ge bond angles stay mostly octahedral-like.** The distribution peaks at 91–93° for every composition. The share
  between 100 and 120° (tetrahedral-like) rises with C, from 0.19 in x0 to 0.25 in x10, while 80–100° falls from 0.54
  to 0.48.
- **Rate.** The 1 K/ps glasses are more octahedral (x0: 0.57 in 80–100°) and more C-clustered (x10: 95% of C in
  clusters of 10 or more, the largest 286 atoms), consistent with their partial crystallization and further C
  segregation.

## C cutoffs

**C cutoffs, checked on the production x10 glasses** (they were set on the small, 12 ps logic-test glass): kept.
In all three 10 K/ps x10 glasses and the 1 K/ps one, g_CC(1.9 Å) = 0.000. At 2.5 Å, g is 0.05–0.09 for Ge–C and
Sb–C and ≤ 0.007 for Te–C, on the tail of peaks at 2.0 and 2.2 Å. Moving the cutoff to 2.4 or 2.6 Å changes the
C coordination of Ge by ≤ 2% and of Sb by 4–6%.

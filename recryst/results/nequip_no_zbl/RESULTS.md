# Recrystallization, nequip_no_zbl: Phase B grid, growth velocity and grains

Homogeneous recrystallization of melt-quenched glasses (10 K/ps quench) in isothermal anneals, 5 compositions ×
Ta 500–700 K (50 K steps) × 3 replicas = 75 runs, `BARO=aniso`, hold ≤ 2 ns, halt at xfracGST 0.65
(`params/nequip_no_zbl.sh`). Q4 criterion 3.9/0.6/4. Sources: `grid_verdict.txt`, `growth_table.csv` (per run),
`growth_summary.csv` (`analysis/plot_growth.py`), `grains_summary.csv` (`analysis/grains.py` +
`analysis/plot_grains.py`), figures in `figures/`. Barostat check: `iso_check.md` (iso = aniso within scatter).

## 1. Verdicts and nucleation

All 75 runs finished. Every (composition, Ta) is USABLE except 700 K for x1, x2p5, x5 and x10 (TOO COLD: no
nucleus in 2 ns). At 700 K, x0 nucleated in 2 of 3 runs. So the common homogeneous window is 500–650 K.

| C (at.%) | t_nuc 500 K | 550 K | 600 K | 650 K | t50 600 K | t50 650 K |
|---|---|---|---|---|---|---|
| 0 (x0) | 53 ± 25 | 66 ± 9 | 47 ± 1 | 98 ± 44 | 275 ± 16 | 317 ± 38 |
| 1.07 (x1) | 145 ± 11 | 115 ± 29 | 95 ± 14 | 146 ± 48 | 423 ± 10 | 444 ± 41 |
| 2.54 (x2p5) | 227 ± 37 | 166 ± 19 | 138 ± 50 | 340 ± 78 | 555 ± 50 | 757 ± 3 |
| 5.14 (x5) | 349 ± 104 | 191 ± 43 | 167 ± 4 | 448 ± 20 | 868 ± 29 | 1091 ± 46 |
| 9.96 (x10) | 430 ± 64 | 360 ± 132 | 315 ± 61 | 889 ± 159 | 956 ± 87 | 1899 ± 98 (n=2) |

Times in ps (mean ± sample std over 3 replicas). t50 uses each composition's end point (X_END 0.65; x10 0.40).
Carbon delays nucleation monotonically at every Ta. The shortest incubation is at 600 K for every composition.

## 2. Growth velocity: which number is an interface velocity

**Conclusion.** The velocity to report is **v_flux** (`grains_summary.csv`). It is the growth of all tracked
crystalline grains, in Te atoms per ps, divided by n_Te × the summed grain area. A merged grain is compared with
the sum of its parents, and births are excluded. Frames are used up to xfracGST 0.45. The `v_growth` of
`recryst_summary.py` (`growth_summary.csv` v_mean, `growth_table.csv`) is **not** an interface velocity in these
runs. It is the radius slope of the largest Q4 cluster, and that cluster spans several grains and grows mainly by
coalescence. Keep it only as a cluster growth rate; do not plot it as v(Ta). For x5 and x10 no interface velocity
exists (grains cannot be segmented: the crystals are too defective). Compare them by t_nuc and t50 only.

Evidence (`figures/grains_v.png`, columns in `grains_summary.csv`):
1. **Coalescence.** Within the 10–25% window, the largest frame-to-frame jump of the largest cluster is 42–100% of
   its total growth across the window (mean per composition and Ta; x0 700 K, a single grain: 6%). 54 of the 57
   runs with a `v_growth` have `single_grain` < 0.8, so the summary already marked them upper bounds.
2. **Budget check.** Each run's grains are born at their observed times (tracks not later lost) and grow from
   r(30 Te) at velocity v. The predicted Te fraction in grains, 1 − exp(−V_ext/V), is then compared with the
   observed fraction at xfracGST 0.45. With v_flux the ratio X_pred/X_obs is 0.69–0.89 for every
   (composition, Ta) with 3 runs. With the cluster `v_growth` it is 3.2–7.3, and that is a floor, because the
   prediction saturates at 1. The small shortfall with v_flux comes from crystal in grains under 30 Te, which the
   tracks do not count.
3. **Single-grain control.** x0 at 700 K (r3) grows from a single nucleus (grain tracking: one grain). There, cluster
   `v_growth` 10.3 m/s and v_flux 9.9 m/s agree. With one grain the methods coincide; with many they do not.
4. **Independent estimates agree.** The per-grain median slope (each grain from birth to its first merge, ≤ 800
   Te; `v_grain_median`) is within a factor of 1.5 of v_flux. Per-grain slopes show no systematic rise with
   grain size: at 650 K, x0 gives 5.0 / 4.8 / 3.8 m/s for grains of 30–150 / 150–400 / ≥ 400 Te. So the small
   grains are not curvature-limited, and v_flux is not a small-size artefact.

v_flux (m/s; ± sample std of the 3 per-run values):

| C (at.%) | 500 K | 550 K | 600 K | 650 K | 700 K |
|---|---|---|---|---|---|
| 0 (x0) | 0.31 ± 0.12 | 0.98 ± 0.34 | 2.68 ± 0.25 | 5.87 ± 0.81 | 9.9 (1 run) |
| 1.07 (x1) | 0.23 ± 0.04 | 0.53 ± 0.08 | 1.51 ± 0.30 | 4.23 ± 0.34 | no nucleus |
| 2.54 (x2p5) | 0.04 ± 0.08 * | 0.32 ± 0.07 | 1.05 ± 0.31 | 2.30 ± 0.38 | no nucleus |

\* x2p5 500 K: grains stay at ~30–150 Te for 2 ns. This is noise-level growth, not a measurement.

- **v(Ta) has no peak inside the window.** It rises about 20-fold from 500 to 650 K for x0 and x1, and x0
  continues to rise up to 700 K. The plateau and peak that the cluster `v_growth` showed (x0: 13.5, 15.6, then 10.3 m/s
  at 600, 650, 700 K) came from coalescence: fewer nuclei at 650–700 K mean fewer merges. The peak of the true
  interface velocity lies above 650 K (above 700 K for x0). Homogeneous runs cannot reach it, because carbon
  cells do not nucleate at 700 K within 2 ns.
- **Carbon slows the interface.** Relative to x0, x1 is slower by 1.4–1.8× and x2p5 by 2.5–3×, at 550–650 K.
- The cluster rate overstates v by 2.6–6× at 600–650 K and by 8–20× at 500 K.
- Caveat: v_flux follows the template-matched Te core of each grain. The Q4 crystalline region around it is
  larger, but if its rim has constant thickness, it moves at the same velocity. These are early-growth values (up
  to xfracGST 0.45), not steady-state ones.

## 3. Grains (x0, x1, x2p5)

Method: OVITO PTM (FCC on the Te sublattice, RMSD 0.15) + grain segmentation, minimum 30 Te, no orphan
adoption. Validation: the glass gives 0 grains, and the count is stable over RMSD 0.10–0.25 (`analysis/grains.py`
docstring).

- **At equal crystallized fraction (xfracGST 0.28)** grain sizes do not depend on carbon. The median core
  d_eq is 1.5–2.0 nm at 500–600 K and 2.4–2.7 nm at 650 K. Grain counts per cell peak at 600 K (x0 14, x1 16,
  x2p5 15).
- **At the 0.65 halt (600/650 K)** carbon gives fewer, larger grains: 32 / 28 / 24 per cell at 600 K and
  11 / 8 / 6 at 650 K. Median d is 3.45 / 3.45 / 4.52 nm at 650 K. This is the opposite of the experimental grain
  refinement by carbon. In the model, carbon slows nucleation (t_nuc ×1.5–3.5) at least as much as it slows the
  interface (×1.4–3). An earlier claim that "C refines grains at 500 K" compared unequal crystal fractions and is
  retracted.
- **Carbon is rejected from grains.** The fraction of C inside grain interiors is 2–10% of the Ge/Sb fraction at
  every Ta and crystal fraction (`figures/grains_carbon.png`). Carbon ends up in the amorphous remainder, not at
  boundaries.

## 4. Open

- The v(Ta) peak and x0's 700 K point (1 run) need the seeded slabs (Phase D, done by someone else) or longer holds.
- x5/x10: growth can be compared only through t_nuc/t50 (section 1).

# Part 3 results: crystallization of GST + x% C

**Final status (2026-11-13; tag `run5_ep301-final`):** calibration done; heating ramps done (no crystallization at
1 K/ps; x0 Tx 571 K at 0.2 K/ps); Phase A done at 600 and 650 K (iso and aniso). Stopped there: the potential is being
retrained, and Part 3 restarts from Part 1 with the new model (`RUNBOOK.md`). Sections 5 and 6 were not run with
run5_ep301. Methods: `recryst/README.md`. The scripts named below (`submit_screen.sh`, `analyze_screen.sh`,
`analyze_ramp_rate.sh`, `submit_aniso.sh`) were replaced after this tag by `scripts/submit_grid.sh` and
`analyze_grid.sh`; paths `runs/...` and `calib/...` are now `runs/run5_ep301/...` and `calib/run5_ep301/...`.

**Read every number here with three caveats:**
- **Dense glass.** The model's glass is as dense as its crystal, a property of its DFT reference (`tests/RESULTS.md`
  1g, 1k). Crystallization expands the cell here, where experiment shows shrinkage, so anything sensitive to the
  glass–crystal density difference (strain, pressure-dependent kinetics) belongs to this reference, not to real GST.
- **MD rates.** Heating rates of 0.2–1 K/ps are ~10¹⁰ times faster than DSC, so absolute Tx are not comparable with
  experiment. The trend with C content is.
- **Ordered glass.** The 10 K/ps glasses already hold crystal-like clusters of up to ~130 Ge/Sb/Te atoms under the
  final criterion. Nucleation is counted only above `--nucleated-size` (≈ 2 × that), and MFPT fits only above each
  group's own glass baseline (`README.md`, "Crystal-like order already in the glass").

## 1. Crystallinity criterion: done
**`q_rc` 3.8 Å, `q_thr` 0.6, `q_nmin` 4**, on the Ge/Sb/Te atoms (`xfracGST`). Calibration jobs 12295527 (54
references, 20 ps each, 300–700 K) and 12308622 (scan to 4.0 Å); `calib/calibrate.out` from `--choose 3.8 0.6 4`
(job 12309345); also `calib/run5_ep301/calib_params.sh`. Per-T values below (`XSTOP` here is calibrate.py's
suggestion; the runs from Phase A on used 0.65, section 4).

| | Lowest crystal reference | Highest glass | Margin |
|---|---|---|---|
| Final (3.8, 0.6, 4) | 0.805 (x5, 700 K) | 0.094 (x0, 300 K) | 0.711 |
| Default (3.6, 0.5, 4) | 0.812 | 0.151 | 0.661 |

- The margin is flat at 3.8–3.9 Å (0.711 / 0.712) and falls at 4.0 Å (0.705). 3.8 Å was kept over the strict
  optimum: the gain is noise, and the cutoff stays further from the ~4.2 Å second-neighbour shell.
- C lowers the crystal reference: at 600 K, x0 0.950, x1 0.951, x2p5 0.916, x5 0.842 (x10 rocksalt disorders within ps
  and has no reference). Hence a per-composition `--x-crystal` and one `XSTOP` per temperature set by x5.
- The glasses read 0.04–0.09, falling with temperature; their largest crystal-like cluster at 550–650 K
  is 103–130 atoms (124–172 under the default).

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

## 2. Heating ramps at 1 K/ps: no crystallization
`scripts/analyze_ramps.sh` → `ramp_summary_h1.txt`, `ramp_tx.txt` (job 12308688; 3 replicas per composition, 300 →
900 K). **None of the 15 ramps crystallizes:** the largest rise of `xfracGST` above its start is 0.115 (x0), against
the 0.2 that `recryst_summary.py` requires, so `Tx_xfrac` is undefined for every composition.

| x (at.% C) | Crystallized | `xfracGST` at 300 K | Peak `xfracGST` | At 900 K | max `sdev_z` |
|---|---|---|---|---|---|
| 0 | 0 of 3 | 0.099 ± 0.005 | 0.174 ± 0.036 | 0.010 | −2.7 |
| 1 | 0 of 3 | 0.087 ± 0.005 | 0.125 ± 0.012 | 0.011 | −1.6 |
| 2.5 | 0 of 3 | 0.079 ± 0.003 | 0.106 ± 0.004 | 0.010 | −2.4 |
| 5 | 0 of 3 | 0.072 ± 0.007 | 0.093 ± 0.008 | 0.013 | −2.2 |
| 10 | 0 of 3 | 0.083 ± 0.006 | 0.095 ± 0.006 | 0.022 | −4.2 |

- **C suppresses the transient order.** The peak rises above the start by about 0.075 for x0 and only 0.01–0.04 for
  the C-containing glasses.
- **x0 nucleates but does not crystallize.** In x0 r2 the largest crystal-like Ge/Sb/Te cluster grows from 134 atoms
  (594 K) past the nucleus size (~250) by 623 K, to 1386 atoms (11% of Ge/Sb/Te) at 774 K, then shrinks and is gone
  by 890 K: at 1 K/ps it cannot grow through the cell before the rising temperature dissolves it.
- **All samples end liquid-like** (`xfracGST` 0.01–0.02 at 900 K). `Tx_H` and `Tx_rho` mostly fall at 780–900 K,
  where the glass softens and its transient order melts; without crystallization they do not mark a Tx.
- No barostat stress (every `sdev_z` < 0).

## 3. Heating-rate check: x0 at 0.2 K/ps crystallizes
`scripts/analyze_ramp_rate.sh` → `ramp_rate_x0.txt`, `ramp_rate_x0_verdict.txt` (job 12308689, x0 r1, 3010 ps).
- **Tx_xfrac = 571 K.** `xfracGST` peaks at 0.67 (the x0 crystal reads ~0.95) and stays crystalline to 900 K (0.58).
  Density drops by 0.008 g/cc across crystallization, the sign this model's dense glass predicts.
- `Tx_H` (726 K) and `Tx_rho` (877 K) disagree with Tx_xfrac; the crystalline fraction is the reliable marker.
- **Large barostat stress:** `sdev_z` = 91 (deviatoric stress 0.5 → 5.0 kbar), far above the threshold of 5. An
  anisotropic rerun of this ramp does not fit one A100's 24 h limit, so the barostat question moves to the screening
  anneals (section 4).
- No rate shift or Kissinger estimate: the 1 K/ps reference has no Tx. Slowing the heating 5× turns no
  crystallization into crystallization at 571 K, so Tx in this model depends strongly on rate.

## 4. Phase A: x0 at 600 and 650 K, iso and aniso: done
`scripts/submit_screen.sh` (TX_X0 900: at 1 K/ps nothing crystallizes below 900 K, so the whole grid passes the guard;
the 0.2 K/ps Tx of 571 K is from a rate 50× slower than the anneal heating and is not a guard), then
`scripts/analyze_screen.sh` (`screen_T<Ta>*.txt`, `screen_aniso_T<Ta>*.txt`, `screen_verdict*.txt`). All 12 runs
crystallized and halted, 0.44–2.5 ns into the hold. Grown crystals plateau at `xfracGST` ≈ 0.71 at 600 K, below the
first halt levels (0.72/0.70) and far below the perfect crystal's 0.95. So `XSTOP` became 0.65 and t_inc/t50 use one
end point, `--x-end 0.65` (commit 04997bc).

| Ta | barostat | verdict | t_nuc (ps) | t_inc (ps) | t50 (ps) | v_growth (m/s) | sdev_z |
|---|---|---|---|---|---|---|---|
| 600 | iso | USABLE, 3 of 3; n_base 160 / 260 | 94, 54, 80 | 63, 52, 59 | 270, 251, 288 | 4.0, 3.5, 3.8 | 16.8, 5.2, 20.3 |
| 600 | aniso | USABLE, 3 of 3; n_base 164 / 260 | 62, 60, 72 | 66, 62, 63 | 278, 244, 273 | 3.2, 5.6, 4.1 | 3.7, 11.9, 7.6 |
| 650 | iso | USABLE, 3 of 3; n_base 120 / 210 | 75, 61, 81 | 121, 125, 121 | 283, 283, 273 | 8.0, 9.1, 12.1 | 15.8, 8.8, 5.2 |
| 650 | aniso | USABLE, 3 of 3; n_base 98 / 210 | 69, 91, 79 | 121, 120, 132 | 302, 285, 279 | 7.4, 10.0, 8.5 | 4.8, 1.9, 2.6 |

(replicas r1, r2, r3.)
- **v_growth about doubles from 600 to 650 K** (≈ 4 → ≈ 9 m/s), with iso and aniso inside each other's spread; t50
  ≈ 250–300 ps at both Ta, so the faster growth at 650 K is offset by a longer incubation (t_inc ≈ 120 vs 60 ps).
- **Barostat:** iso and aniso give the same kinetics, but every iso run ends with `sdev_z` 5–20 (stress the cubic box
  cannot relax); aniso is lower (2–12) and fully relieved at 650 K. Decision (2026-11-13): aniso for everything after
  (`params/run5_ep301.sh` BARO).
- **Second grains:** every run shows a short-lived second cluster of `--nucleated-size` during the v_growth window
  (`single_grain` 0 under the old all-or-nothing flag; median second cluster 9–90 atoms). Hence `single_grain` is now
  the fraction of window frames without one.
- n_base / N is 0.47–0.63: the glass's own ordered patches reach about half the nucleation threshold at Ta.
- 500 K aniso was started and cancelled (2 partial runs, `runs/run5_ep301/anneal_x0_aniso_T500_r1-2`); 550 and 700 K
  were not run.

## Provenance
Branch `part3`. Criterion and scripts: commits 02b8bf1 (grid to 4.0 Å), f72fd2b (per-composition `--x-crystal`),
aeade34 and 39d3592 (`rate_compare.py` and its checks), 9f2ddaa (`TAG`), 44ad074 and ba1d107 (`scripts/`). Model
run5_ep301 (`models/provenance.md`); dt 2 fs; 12.4k–13.8k-atom 3×3×3 cells; glasses from Part 2 at 10 K/ps
(`meltquench/runs/run5_ep301/<cell>_q10_r<1-3>`). Phase A: commits e77f3d0, 04997bc, 350ddc9.

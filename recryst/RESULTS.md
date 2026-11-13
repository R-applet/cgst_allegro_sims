# Part 3 results: crystallization of GST + x% C

**Status (2026-11-12):** calibration done; heating ramps done (no crystallization at 1 K/ps; x0 Tx 571 K at
0.2 K/ps); screening and production anneals not started. Sections marked _pending_ name the script that fills them (`scripts/`, run order in
`scripts/README.md`). Methods are in `README.md`; this file records what came out.

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
(job 12309345). Full table: `README.md` section 1, "Result".

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

## 4. Phase A: x0 over the temperature grid, and the barostat: _pending_
`scripts/submit_screen.sh`, then `scripts/analyze_screen.sh`: TOO HOT / TOO COLD / USABLE per Ta, x0 r1–r3.
**Guard input: `TX_X0=900`, `TX_X0_STD=0`.** The guard keeps an anneal from crystallizing during its 10 K/ps heating
to Ta, so it needs a Tx measured at a rate no faster than that heating. At 1 K/ps nothing crystallizes below 900 K,
so the whole calibrated grid, 500–700 K, passes. The 0.2 K/ps Tx (571 K) belongs to a rate 50× slower than the
anneal heating and would wrongly exclude all five.
**Phase A (x0, 500–700 K, 3 replicas):** iso/aniso pairs at 600 and 650 K first (`BARO=aniso`, runs
`anneal_x0_aniso_T<Ta>_r*`), because the 0.2 K/ps x0 crystal built 5 kbar of deviatoric stress (section 3); then 500,
550 and 700 K with the chosen barostat. Grown x0 crystals plateau at `xfracGST` ≈ 0.71 at 600 K, below the first
halt levels (0.72/0.70), so later runs halt at `XSTOP` = 0.65 and t_inc/t50 use one end point, `--x-end 0.65`
(`README.md`, "Halt level"). Record per Ta the verdicts, x0 `v_growth` per run, the iso-vs-aniso
comparison at 600 and 650 K (`rate_compare.py` on `screen_T<Ta>_clusters.txt` and `screen_aniso_T<Ta>_clusters.txt`,
t50 and `v_growth`), and which barostat the rest of the grid uses, with the reason.

## 5. Growth velocity vs Ta per composition (homogeneous): _pending_
Phase B (`recryst/README.md`, "Temperature grid"): every composition over the Ta where nucleation happens, 3 replicas
each, reusing the Phase A x0 runs; one row per run (composition, Ta, replica, barostat, nucleated, t_nuc,
`v_growth`, `single_grain`, t50) and the figures: `v_growth` vs Ta per composition (replicas as points, median, n per
point), its distribution per composition and Ta, and the fraction of runs that nucleated vs Ta.

To record: where each composition's v(Ta) peaks, or that it rises or falls across the whole homogeneous window; how C
shifts and scales it; runs with `single_grain` = 0; any (composition, Ta) whose `n_base` exceeds half of
`--nucleated-size` (glass aging). Nucleation rates (`rate_compare.py`) are by-products with ~58% error at 3 runs.

## 6. Barostat check: _pending, only if triggered_
`scripts/submit_aniso.sh` / `scripts/analyze_ramp_aniso.sh` for any crystallized set with `sdev_z` > 5. Record
whether the anisotropic box removes the stress and shifts Tx or t50.

## Provenance
Branch `part3`. Criterion and scripts: commits 02b8bf1 (grid to 4.0 Å), f72fd2b (per-composition `--x-crystal`),
aeade34 and 39d3592 (`rate_compare.py` and its checks), 9f2ddaa (`TAG`), 44ad074 and ba1d107 (`scripts/`). Model
run5_ep301 (`models/provenance.md`); dt 2 fs; 12.4k–13.8k-atom 3×3×3 cells; glasses from Part 2 at 10 K/ps
(`meltquench/runs/<cell>_q10_r<1-3>`).

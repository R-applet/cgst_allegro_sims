# Part 3 results: crystallization of GST + x% C

**Status (2026-11-10):** calibration done; 1 K/ps and 0.2 K/ps heating ramps running; screening and production
anneals not started. Sections marked _pending_ name the script that fills them (`scripts/`, run order in
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

## 2. Crystallization temperature Tx vs C (1 K/ps): _pending_
`scripts/analyze_ramps.sh` → `ramp_tx.txt` (jobs 12308688, 3 replicas per composition).

| x (at.% C) | Crystallized | Tx_xfrac (K) | Tx_H (K) | Δρ at Tx (g/cc) | max sdev_z |
|---|---|---|---|---|---|
| 0 | | | | | |
| 1 | | | | | |
| 2.5 | | | | | |
| 5 | | | | | |
| 10 | | | | | |

To record: the trend with C (expected to rise); whether x5/x10 crystallize by 900 K; agreement of Tx_H with
Tx_xfrac; sign of Δρ (expected negative here, see dense glass); any composition with `sdev_z` > 5.

## 3. Heating-rate check (x0 r1, 0.2 vs 1 K/ps): _pending_
`scripts/analyze_ramp_rate.sh` (job 12308689). Tx shift against the 1 K/ps replica spread; two-point Kissinger Ea
(order of magnitude only).

## 4. Screening: choice of the anneal temperature: _pending_
`scripts/submit_screen.sh` (only Ta below x0 Tx − max(25 K, 2 std)), then `scripts/analyze_screen.sh`: TOO HOT /
TOO COLD / USABLE per Ta, x0 r1–r3. The production Ta is chosen at the review checkpoint and recorded here with the
reason.

## 5. Isothermal kinetics vs C at one Ta: _pending_
`scripts/submit_production.sh`, then `scripts/analyze_production.sh` and `analysis/rate_compare.py`; 10 replicas per
composition.

| x (at.% C) | Nucleated (of 10) | J_surv (m⁻³ s⁻¹) | t50 (ps) | v_growth (m/s) | n_base / N |
|---|---|---|---|---|---|
| 0 | | | | | |
| 1 | | | | | |
| 2.5 | | | | | |
| 5 | | | | | |
| 10 | | | | | |

To record: rate ratios between compositions with their ~95% intervals (Bonferroni over pairs); the glass-to-glass
test per composition (low power: p > 0.05 does not show the glasses agree); MFPT n* and τ_J where defined; any
composition whose `n_base` exceeds half of `--nucleated-size` (glass aging).

## 6. Barostat check: _pending, only if triggered_
`scripts/submit_aniso.sh` / `scripts/analyze_ramp_aniso.sh` for any crystallized set with `sdev_z` > 5. Record
whether the anisotropic box removes the stress and shifts Tx or t50.

## Provenance
Branch `part3`. Criterion and scripts: commits 02b8bf1 (grid to 4.0 Å), f72fd2b (per-composition `--x-crystal`),
aeade34 and 39d3592 (`rate_compare.py` and its checks), 9f2ddaa (`TAG`), 44ad074 and ba1d107 (`scripts/`). Model
run5_ep301 (`models/provenance.md`); dt 2 fs; 12.4k–13.8k-atom 3×3×3 cells; glasses from Part 2 at 10 K/ps
(`meltquench/runs/<cell>_q10_r<1-3>`).

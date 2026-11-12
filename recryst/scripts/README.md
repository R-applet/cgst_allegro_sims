# Part 3 workflow scripts

Wrappers for the steps after calibration (`../README.md`, "Choosing Ta" and "Barostat"). They carry the final
criterion (3.8, 0.6, 4) and its per-Ta values (500–700 K). They refuse to submit or analyse when the inputs do not
match: wrong criterion, `XSTOP` or hold length, unfinished or duplicate runs, or a temperature too close to a ramp Tx.
Tested on fake run trees (2026-11-10); `analyze_ramps.sh` and `analyze_ramp_rate.sh` have since run on the real ramps,
the others not yet on real outputs. Run from anywhere; `RECRYST` and `PY` override
the run tree and the Python (used by the tests). `--dry-run` prints `sbatch` commands without submitting; `FORCE=1`
turns a consistency stop into a warning where the script allows it.

In order:

| Script | When | What |
|---|---|---|
| `analyze_ramps.sh` | 1 K/ps ramps done | criterion check, `ramp_summary_h1.txt`, per-composition Tx from per-run rows (`ramp_tx.txt`), prints the `submit_screen.sh` line when all 3 x0 ramps crystallized |
| `analyze_ramp_rate.sh` | 0.2 K/ps ramp done | x0 r1 at 0.2 vs 1 K/ps: Tx shift against the 1 K/ps replica std, rough two-point Kissinger Ea |
| `submit_screen.sh` | after the ramps | Phase A: x0 r1-r3 at 500–700 K (`TAS` for a subset) below x0 Tx − max(25 K, 2 std); needs `TX_X0`, `TX_X0_STD` (a Tx at a rate no faster than 10 K/ps; 900 when 1 K/ps does not crystallize); `BARO=aniso` for the aniso set (`TAG=aniso`) |
| `analyze_screen.sh summary` / `verdict` | screening done | checks (incl. barostat from `log.anneal.1`), one perc cluster job; then TOO HOT / TOO COLD / USABLE per Ta and the hottest usable Ta (a suggestion); `BARO=aniso` for the aniso set, outputs `screen_aniso_*`; iso vs aniso via `rate_compare.py` on both cluster files |
| `submit_production.sh` | superseded | the earlier one-Ta design (all compositions × 10 at one Ta); to be replaced by the Phase B grid scripts, see `../README.md` "Temperature grid". Was: after the review | all compositions × 10 at one Ta; needs `REVIEWED=1` and `ramp_tx.txt`; reuses the matching screening runs as x0 r1-r3 |
| `analyze_production.sh summary` / `compare` | production done | checks, overview, 5 perc cluster jobs; then `../../analysis/rate_compare.py` |
| `submit_aniso.sh` | a set flagged with `sdev_z` > 5 | `TAG=aniso` rerun of a production, screening or ramp set |
| `analyze_ramp_aniso.sh` | ramp aniso reruns done | iso vs aniso Tx, Welch test, stress check |

Group means in `recryst_summary.py` skip NaN while the group line still counts every run. So these scripts count
crystallized or nucleated runs from the per-run rows. `--nucleated-size` (250/260/210) and the per-composition
`--x-crystal` values are from `../calib/calibrate.out` (3.8, 0.6, 4), checked for commit 5cfeee0; recheck them if it is
regenerated.

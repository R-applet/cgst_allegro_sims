# Part 3 workflow scripts

Wrappers for the steps after calibration (`../README.md`, "Choosing Ta" and "Barostat"). They carry the final
criterion (3.8, 0.6, 4) and its per-Ta values (550/600/650 K). They refuse to submit or analyse when the inputs do not
match: wrong criterion, `XSTOP` or hold length, unfinished or duplicate runs, or a temperature too close to a ramp Tx.
Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; `RECRYST` and `PY` override
the run tree and the Python (used by the tests). `--dry-run` prints `sbatch` commands without submitting; `FORCE=1`
turns a consistency stop into a warning where the script allows it.

In order:

| Script | When | What |
|---|---|---|
| `analyze_ramps.sh` | 1 K/ps ramps done | criterion check, `ramp_summary_h1.txt`, per-composition Tx from per-run rows (`ramp_tx.txt`), prints the `submit_screen.sh` line when all 3 x0 ramps crystallized |
| `submit_screen.sh` | after the ramps | x0 r1-r3 at each of 550/600/650 K below x0 Tx − max(25 K, 2 std); needs `TX_X0`, `TX_X0_STD` |
| `analyze_screen.sh summary` / `verdict` | screening done | checks, one perc cluster job; then TOO HOT / TOO COLD / USABLE per Ta and the hottest usable Ta (a suggestion) |
| `submit_production.sh` | after the review | all compositions × 10 at one Ta; needs `REVIEWED=1` and `ramp_tx.txt`; reuses the matching screening runs as x0 r1-r3 |
| `analyze_production.sh summary` / `compare` | production done | checks, overview, 5 perc cluster jobs; then `../../analysis/rate_compare.py` |
| `submit_aniso.sh` | a set flagged with `sdev_z` > 5 | `TAG=aniso` rerun of a production, screening or ramp set |
| `analyze_ramp_aniso.sh` | ramp aniso reruns done | iso vs aniso Tx, Welch test, stress check |

Group means in `recryst_summary.py` skip NaN while the group line still counts every run. So these scripts count
crystallized or nucleated runs from the per-run rows. `--nucleated-size` (250/260/210) and the per-composition
`--x-crystal` values are from `../calib/calibrate.out` (3.8, 0.6, 4); confirm them when it is regenerated.

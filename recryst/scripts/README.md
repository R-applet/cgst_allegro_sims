# recryst workflow scripts

Wrappers for the recrystallization steps after calibration, in the order of `../../RUNBOOK.md`. They hold no model's numbers.
`common.sh` reads everything from `recryst/params/<MODEL_ID>.sh`, which also sources the generated
`recryst/calib/<MODEL_ID>/calib_params.sh`: criterion, NUC, XC_\*, GLASS_\*, XSTOP, X_END, TX_GUARD, BARO, RUNTAG,
TAS, NREP and MAX_NS. The scripts stop if either file is missing. They also refuse to submit or analyse when the
inputs do not match:
- the wrong criterion, barostat, model, `XSTOP` or hold length;
- unfinished or duplicate runs;
- a Ta outside the calibration temperatures or not below `TX_GUARD` − 25 K.

Run them from anywhere. `--dry-run` prints the `sbatch` commands without submitting. `FORCE=1` turns a consistency
stop into a warning. `RECRYST` points at another run tree (tests) and `PY` overrides the Python. Outputs go to
`results/<MODEL_ID>/`, and each starts with `#` lines naming the model, criterion and end point.

| Script | When | What |
|---|---|---|
| `common.sh` | sourced by the others | paths (`RUNS`, `RESULTS`), params, `check`/`die`, `n_end`, `header`, and `check_anneal_set`: the checks every anneal analysis repeats |
| `analyze_ramps.sh` | the `HRATE` ramps are done | completion, criterion and model checks; `ramp_h<HRATE>.txt` and `ramp_tx_h<HRATE>.txt` (Tx_xfrac per composition from the per-run rows) |
| `submit_grid.sh` | after the ramps | anneals for `CELLS` × `TAS` × `NREP` (Phase A: `CELLS=x0`; Phase B: all five); skips a (cell, Ta) whose runs exist, so Phase B reuses Phase A |
| `analyze_grid.sh summary` / `verdict` | the grid set is done | checks, `grid_<cell>[_<RUNTAG>]_T<Ta>.txt`, one perc cluster job (`..._clusters.txt`); then `grid_verdict.txt` (TOO HOT / TOO COLD / USABLE per cell and Ta) and `growth_table.csv` (per run: t_nuc, t50, v_growth, single_grain, sdev_z) |

`recryst_summary.py` group means skip NaN while the group line counts every run. For that reason these scripts count
crystallized or nucleated runs from the per-run rows.

Removed after run5_ep301 (tag `run5_ep301-final` has them; their outputs are in `../results/run5_ep301/`):
- `submit_screen.sh` and `analyze_screen.sh`, replaced by the grid scripts with `CELLS=x0`;
- `submit_production.sh` and `analyze_production.sh`, the one-Ta design;
- `submit_aniso.sh` and `analyze_ramp_aniso.sh`, since aniso is now the default barostat (`BARO` in params);
- `analyze_ramp_rate.sh`, which compared against 1 K/ps ramps that are no longer run.

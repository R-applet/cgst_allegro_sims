# Design numbers for MODEL_ID=run5_ep301, each with where it came from. Sourced by meltquench/submit.sh,
# recryst/submit_ramp.sh and recryst/scripts/common.sh (so by every Part 3 script). For a new model, copy this file to
# params/<MODEL_ID>.sh and replace every value from that model's own pilot measurements (RUNBOOK.md); nothing here
# carries over between models. The calibrated criterion and per-T tables are generated, not set here:
# recryst/calib/<MODEL_ID>/calib_params.sh (recryst/calib/make_params.py), sourced at the end when it exists.
# Every job sources this file when it starts, including each continuation of an anneal chain: do not change the
# criterion or BARO while runs are in flight (XSTOP and MAX_NS are passed along the chain explicitly).

# Part 2, melt-quench (meltquench/in.meltquench)
TMELT=1500          # K. Superheated melting on a 10 K/ps heat: Tm_app 1129 K (x0) to 984 K (x10)
                    #   (results/run5_ep301/report); 1500 K gives a fast liquid (MSD gate passed in all 17 runs).
HOLD_PS=100         # ps at TMELT; every run passed the MSD gate (>= 100 A^2) with it.
QRATE=10            # K/ps. 1 K/ps partially crystallizes the glass (xfracGST 0.28 vs 0.13-0.16), so Part 3 uses 10.

# Part 3, ramp (recryst/in.ramp)
TMAX=900            # K. Ramp ceiling, below the superheated Tm (~1090 K at 2 K/ps, reference md_npt_cubic_gst).
HRATE=0.2           # K/ps. At 1 K/ps no composition crystallized by 900 K; at 0.2 K/ps x0 r1 did (Tx_xfrac 571 K)
                    #   (recryst/results/run5_ep301/RESULTS.md sections 2-3).
TX_GUARD=900        # K. Upper bound for an anneal Ta: a Tx at a heating rate comparable to the anneal's 10 K/ps heat
                    #   (here: none below 900 K at 1 K/ps). The slower 0.2 K/ps Tx (571 K) is not a guard: it would
                    #   exclude Ta where the 10 K/ps heat does not crystallize. The per-run check is analyze_grid.sh's
                    #   TOO HOT verdict (crystallized during the heat or within 20 ps).

# Part 3, isothermal anneals (recryst/in.anneal, recryst/scripts)
BARO=aniso          # x0 at 600/650 K: iso and aniso give the same t_inc/t50/v_growth, but iso leaves sdev_z 5-20
                    #   (stress the iso box cannot relax); aniso was chosen 2026-11-13.
RUNTAG=aniso        # run-name label: run5_ep301 has iso and aniso sets side by side (anneal_x0_aniso_T600_r1). For a
                    #   model run with one barostat only, leave it empty.
XSTOP=0.65          # fix halt on xfracGST. A crystal grown in the glass plateaus near 0.71 at 600 K (x0, both
                    #   barostats), far below the perfect crystal's 0.95; 0.65 is reached by every crystallizing run.
X_END=0.65          # one end point for t_inc/t50 in every run (recryst_summary.py --x-end); <= XSTOP.
MAX_NS=5            # ns hold. Non-halting runs cost ~40 h on one A100.
NREP=3              # replicas per (composition, Ta); more where a rate needs them.
TAS="500 550 600 650 700"   # the grid; must be calibration temperatures (CALIB_TS).

_calib=$(dirname "${BASH_SOURCE[0]}")/../recryst/calib/$MODEL_ID/calib_params.sh
[ -e "$_calib" ] && source "$_calib"
unset _calib

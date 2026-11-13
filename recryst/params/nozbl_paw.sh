# Recrystallization design numbers for MODEL_ID=nozbl_paw. Sourced by recryst/submit_anneal.sh, submit_ramp.sh,
# calib/submit.sh and scripts/common.sh; sources meltquench/params/nozbl_paw.sh (QRATE, SIZE, NGPU) and the generated
# recryst/calib/nozbl_paw/calib_params.sh. Set 2026-11-13: MAX_NS (2 ns) and RUNTAG (one barostat). Every other value
# is PROVISIONAL, copied from run5_ep301 with run5_ep301's reasons below; this model's calibration, ramp and Phase A
# pilot replace them (RUNBOOK.md, recryst). Every job sources this file when it starts, including each continuation of
# an anneal chain: do not change the criterion or BARO while runs are in flight.

# Ramp (recryst/in.ramp)
TMAX=900            # K. Ramp ceiling, below the superheated Tm (~1090 K at 2 K/ps, reference md_npt_cubic_gst).
HRATE=0.2           # K/ps. At 1 K/ps no composition crystallized by 900 K; at 0.2 K/ps x0 r1 did (Tx_xfrac 571 K)
                    #   (recryst/results/run5_ep301/RESULTS.md sections 2-3).
TX_GUARD=900        # K. Upper bound for an anneal Ta: a Tx at a heating rate comparable to the anneal's 10 K/ps heat
                    #   (here: none below 900 K at 1 K/ps). The slower 0.2 K/ps Tx (571 K) is not a guard: it would
                    #   exclude Ta where the 10 K/ps heat does not crystallize. The per-run check is analyze_grid.sh's
                    #   TOO HOT verdict (crystallized during the heat or within 20 ps).

# Isothermal anneals (recryst/in.anneal, recryst/scripts)
BARO=aniso          # x0 at 600/650 K: iso and aniso give the same t_inc/t50/v_growth, but iso leaves sdev_z 5-20
                    #   (stress the iso box cannot relax); aniso was chosen 2026-11-13.
RUNTAG=""           # one barostat only (BARO), so no run-name label
XSTOP=0.65          # fix halt on xfracGST. A crystal grown in the glass plateaus near 0.71 at 600 K (x0, both
                    #   barostats), far below the perfect crystal's 0.95; 0.65 is reached by every crystallizing run.
X_END=0.65          # one end point for t_inc/t50 in every run (recryst_summary.py --x-end); <= XSTOP.
MAX_NS=2            # ns hold, decided 2026-11-13. At 444 on 2 A100s (2.59 ns/day) a non-halting run is ~19 h, one job.
                    #   Nucleation exposure (volume x time) is 2.37 x 2 = 4.7 run5 3x3x3 ns, about run5's 5 ns.
NREP=3              # replicas per (composition, Ta); more where a rate needs them.
TAS="500 550 600 650 700"   # the grid; must be calibration temperatures (CALIB_TS).

_here=$(dirname "${BASH_SOURCE[0]}")
source "$_here/../../meltquench/params/$MODEL_ID.sh"     # QRATE, SIZE (and the melt-quench settings, for reference)
_calib=$_here/../calib/$MODEL_ID/calib_params.sh
[ -e "$_calib" ] && source "$_calib"
unset _calib _here

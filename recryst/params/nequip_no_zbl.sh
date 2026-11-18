# Recrystallization design numbers for MODEL_ID=nequip_no_zbl. Sourced by recryst/submit_anneal.sh, submit_ramp.sh,
# calib/submit.sh and scripts/common.sh; sources meltquench/params/nequip_no_zbl.sh (QRATE, SIZE, NGPU) and the generated
# recryst/calib/nequip_no_zbl/calib_params.sh. Every job sources this file when it starts, including each continuation of
# an anneal chain: do not change the criterion or BARO while runs are in flight. Evidence is nequip_no_zbl's own.

# Ramp (recryst/in.ramp)
TMAX=900            # K. Ramp ceiling, below the superheated melting point: nequip_no_zbl Tm_app 1139 K (x0) and 983 K (x10)
                    #   on the 10 K/ps heat (meltquench/results/nequip_no_zbl/RESULTS.md).
HRATE=0.2           # K/ps. nequip_no_zbl x0 r1 crystallizes at Tx_xfrac 583 K, x5 r1 at 650 K; x10 r1 not below TMAX
                    #   (results/nequip_no_zbl/ramp_tx_h0.2.txt). Faster ramps were not run for this model.
TX_GUARD=900        # K. Upper bound for an anneal Ta: a Tx at a heating rate comparable to the anneal's 10 K/ps heat.
                    #   None measured for nequip_no_zbl, so TMAX. The
                    #   0.2 K/ps Tx (583 K) is not a guard: it would exclude Ta where the 10 K/ps heat does not
                    #   crystallize. The per-run check is analyze_grid.sh's TOO HOT verdict (crystallized during the heat
                    #   or within 20 ps); none in Phase A.

# Isothermal anneals (recryst/in.anneal, recryst/scripts)
BARO_DEFAULT=aniso  # the production barostat. aniso leaves sdev_z 1.6-17.5 in the 12 crystallized x0 Phase A runs (above 5
                    #   in 4), with no visible effect on t50. Iso/aniso equivalence of t_inc/t50/v_growth not checked for
                    #   this model (the RUNTAG=iso x0 set at 600/650 K was submitted 2026-11-17 and cancelled 2026-11-18).
BARO=${BARO:-$BARO_DEFAULT}  # override per submission only together with a RUNTAG (submit_anneal.sh refuses otherwise):
RUNTAG=${RUNTAG-}   #   BARO=iso RUNTAG=iso TAS="600 650" CELLS=x0 bash scripts/submit_grid.sh; analysis with the same two.
XSTOP=0.65          # fix halt on xfracGST. nequip_no_zbl Phase A x0: a crystal grown in the glass levels off near 0.65-0.67 at
                    #   550-700 K (0.2 K/ps ramp peak 0.666) and was still at 0.55-0.56, slowing, after 2 ns at 500 K; the
                    #   perfect crystal reads 0.95. Kept at 0.65 for every composition (decided 2026-11-17): C-rich crystals
                    #   will not reach it and run the full MAX_NS. Only the cost depends on it; v_growth does not.
X_END=0.65          # one end point for t_inc/t50 in every run (recryst_summary.py --x-end); <= XSTOP. PROVISIONAL: set after
                    #   Phase B to the lowest level every crystallizing run reaches (all compositions, all Ta), likely ~0.5.
MAX_NS=2            # ns hold, decided 2026-11-13. At 444 on 2 A100s (2.59 ns/day) a non-halting run is ~19 h, one job.
                    #   Nucleation exposure (volume x time) is 2.37 x 2 = 4.7 ns of a 333 cell.
NREP=3              # replicas per (composition, Ta); more where a rate needs them.
TAS="500 550 600 650 700"   # the grid; must be calibration temperatures (CALIB_TS).

_here=$(dirname "${BASH_SOURCE[0]}")
source "$_here/../../meltquench/params/$MODEL_ID.sh"     # QRATE, SIZE (and the melt-quench settings, for reference)
_calib=$_here/../calib/$MODEL_ID/calib_params.sh
[ -e "$_calib" ] && source "$_calib"
unset _calib _here

#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# x0 screening anneals (recryst/README.md, section 3, "Choosing Ta", step 1):
# x0 at 500/550/600/650/700 K (the calibrated range; TAS="600 650" for a subset), 3 replicas each (array 0-2 ->
# x0 r1-r3, glasses q10_r1-r3), up to 5 ns, fix halt at XSTOP.
# Final calibration (recryst/README.md, section 1 "Result"): q_rc 3.8, q_thr 0.6, q_nmin 4.
#
# Usage, after the 1 K/ps ramp analysis (ramp_summary_h1.txt, group ramp_x0_h1):
#   TX_X0=<x0 Tx, K> TX_X0_STD=<its sample std, K> [BARO=iso|aniso] bash scripts/submit_screen.sh [--dry-run]
# A TA is submitted only if TA < TX_X0 - max(25 K, 2 x TX_X0_STD), so the anneal cannot crystallize during its 10 K/ps
# heating to TA. TX_X0 must therefore be a Tx measured at a heating rate no faster than 10 K/ps: the 1 K/ps Tx, or
# 900 when the 1 K/ps ramps do not crystallize below 900 K (RESULTS.md section 4). A Tx from a much slower ramp (the
# 0.2 K/ps 571 K) is too strict. The margin covers the replica spread.
# BARO=aniso runs the same tasks (seeds, glasses) with -var baro aniso and TAG=aniso, into
# runs/anneal_x0_aniso_T<TA>_r* (recryst/README.md, "Barostat"); default iso. Submit both for iso/aniso pairs.
# A TA whose runs/anneal_x0[_aniso]_T<TA>_r* already exist is skipped (no double submission); iso and aniso are
# checked separately.
set -euo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
TX_X0=${TX_X0:?set TX_X0 from the ramp analysis (x0 1 K/ps Tx_xfrac mean, K)}
TX_X0_STD=${TX_X0_STD:?set TX_X0_STD (sample std over the 3 x0 ramps, K)}
BARO=${BARO:-iso}
case $BARO in iso) TAGP="" ;; aniso) TAGP="_aniso" ;; *) echo "BARO must be iso or aniso, not '$BARO'" >&2; exit 1 ;; esac
unset TAG                                   # an inherited TAG would rename the iso runs (submit_anneal.sh reads it)

# Criterion, used in-run by fix halt and the dumped c_ncb. sbatch --export=ALL carries EXTRA_VARS into the job, and
# each continuation inherits it the same way, so the criterion stays fixed along a chain.
export EXTRA_VARS="-var q_rc 3.8 -var q_thr 0.6 -var q_nmin 4${TAGP:+ -var baro aniso}"
declare -A XSTOP=( [500]=0.75 [550]=0.73 [600]=0.72 [650]=0.70 [700]=0.68 )   # 0.85 x lowest crystal ref at TA (x5)
TAS=${TAS:-500 550 600 650 700}
for TA in $TAS; do
    [ -n "${XSTOP[$TA]:-}" ] || { echo "TA $TA is not calibrated (500-700 K in 50 K steps)" >&2; exit 1; }
done

limit=$(awk -v tx=$TX_X0 -v sd=$TX_X0_STD 'BEGIN { m = 2 * sd; if (m < 25) m = 25; printf "%.1f", tx - m }')
echo "x0 Tx $TX_X0 +- $TX_X0_STD K -> screening TA must be below $limit K"
for TA in $TAS; do
    if awk -v t=$TA -v l=$limit 'BEGIN { exit !(t >= l) }'; then
        echo "TA $TA: SKIP, not below $limit K (would risk crystallizing during the heating)"; continue
    fi
    if compgen -G "runs/anneal_x0${TAGP}_T${TA}_r*" > /dev/null; then
        echo "TA $TA: SKIP, runs/anneal_x0${TAGP}_T${TA}_r* already exist"; continue
    fi
    # One perc A100-40GB per run (strachan A30s: ~5-day backlog on 2026-11-10). Up to 9 runs at once.
    cmd=(sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1
         --array=0-2 --export=ALL,TA=$TA,XSTOP=${XSTOP[$TA]}${TAGP:+,TAG=aniso} submit_anneal.sh)
    echo "TA $TA: ${cmd[*]}  (EXTRA_VARS=$EXTRA_VARS)"
    [ $DRY = 1 ] || "${cmd[@]}"
done

# If every TA is skipped as too hot, screen colder (e.g. 450/500 K; XSTOP from calibrate.out at 500 K is 0.75, and
# 450 K is not a calibration temperature -- use 500 K's values or add 450 K to calib/submit.sh).
# Analysis: scripts/analyze_screen.sh, with the same BARO (x0's own --x-crystal 0.951 / 0.950 / 0.948 and
# --nucleated-size 250 / 260 / 210 at 550 / 600 / 650 K, checked against calib/calibrate.out, commit 5cfeee0).

#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# Anisotropic-barostat reruns (recryst/README.md, "Barostat"): if sdev_z > 5 in a run that
# crystallized, rerun the whole replica set of that composition with -var baro aniso, TAG=aniso (commit 9f2ddaa:
# own directories runs/anneal_<cell>_aniso_T<Ta>_r<rep> / runs/ramp_<cell>_aniso_h<rate>_r<rep>, same seeds and
# glasses, own replica group), and compare t50 (anneals) or Tx (ramps). Final criterion 3.8/0.6/4.
#   KIND=prod   CELL=<cell> TA=<Ta> bash scripts/submit_aniso.sh [--dry-run]   production set, NREP=10
#   KIND=screen TA=<Ta>             bash scripts/submit_aniso.sh [--dry-run]   x0 screening set, NREP=3
#   KIND=ramp   CELL=<cell>         bash scripts/submit_aniso.sh [--dry-run]   1 K/ps ramps, 3 replicas
# Refuses unless: the analysis flagged that set (prod_overview.txt / screen_verdict.txt / ramp_tx.txt; FORCE=1 to
# rerun anyway); the iso runs it pairs with are finished with the final criterion (and, for anneals, the same XSTOP
# and final step); no aniso directory of that set exists yet.
set -euo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
die() { echo "REFUSED: $*" >&2; exit 1; }
flag() { [ "${FORCE:-0}" = 1 ] && { echo "WARNING (FORCE=1): $*"; return; }; die "$*"; }
KIND=${KIND:?prod, screen or ramp}
export EXTRA_VARS="-var q_rc 3.8 -var q_thr 0.6 -var q_nmin 4 -var baro aniso"
declare -A CI=( [x0]=0 [x1]=1 [x2p5]=2 [x5]=3 [x10]=4 )          # CELLS order in submit_anneal.sh / submit_ramp.sh

case $KIND in
  prod|screen)
    TA=${TA:?set TA}
    case " 500 550 600 650 700 " in *" $TA "*) ;; *) die "TA $TA is not calibrated (500-700 K)" ;; esac
    # the aniso set halts where the iso set it pairs with halted (XSTOP changed to 0.65 on 2026-11-13)
    XSTOP=$(grep -ho 'stop at xfracGST > [0-9.]*' runs/anneal_${CELL:-x0}_T${TA}_r1/anneal_done.txt 2>/dev/null \
            | awk '{print $NF}')
    [ -n "$XSTOP" ] || die "no finished iso run at TA=$TA to take XSTOP from"
    if [ $KIND = prod ]; then CELL=${CELL:?set CELL}; NREP=10; src=prod_overview.txt
        [ -e $src ] || die "$src missing (production analysis 'summary' stage)"
        n=$(awk -v c=$CELL '$1 == c { for (i = 1; i <= NF; i++) if ($i == "5:") print $(i + 1) + 0 }' $src)
        [ "${n:-0}" -gt 0 ] || flag "$src: no crystallized $CELL run with sdev_z > 5 (got '${n:-none}')"
    else CELL=x0; NREP=3; src=screen_verdict.txt
        [ -e $src ] || die "$src missing (screening analysis 'verdict' stage)"
        grep -q "^T$TA:.*sdev_z>5:" $src || flag "$src: T$TA has no crystallized run with sdev_z > 5"
    fi
    [ -n "${CI[$CELL]:-}" ] || die "unknown CELL $CELL"
    lo=$(( ${CI[$CELL]} * NREP )); hi=$(( lo + NREP - 1 ))
    want="(stop at xfracGST > $XSTOP or step $(( 5000 + 50 * (TA - 300) + 2500000 )))"
    for r in $(seq 1 $NREP); do d=runs/anneal_${CELL}_T${TA}_r$r
        [ -e $d/anneal_done.txt ] || die "$d not finished: the iso set must be complete to compare"
        read -r _ _ k1 v1 k2 v2 k3 v3 < $d/hold_start.txt
        [ "$v1 $v2 $v3" = "3.8 0.6 4" ] || die "$d criterion $v1 $v2 $v3"
        grep -qF "$want" $d/anneal_done.txt || die "$d: $(grep -o '(stop at.*)' $d/anneal_done.txt), expected $want"
    done
    ! compgen -G "runs/anneal_${CELL}_aniso_T${TA}_r*" > /dev/null || die "runs/anneal_${CELL}_aniso_T${TA}_r* exist"
    cmd=(sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1
         --array=$lo-$hi --export=ALL,TA=$TA,NREP=$NREP,XSTOP=$XSTOP,TAG=aniso submit_anneal.sh)
    cmp="python ../analysis/recryst_summary.py --x-end 0.65 runs/anneal_${CELL}_T${TA}_r* runs/anneal_${CELL}_aniso_T${TA}_r*"
    ;;
  ramp)
    CELL=${CELL:?set CELL}; [ -n "${CI[$CELL]:-}" ] || die "unknown CELL $CELL"; src=ramp_tx.txt
    [ -e $src ] || die "$src missing (ramp analysis)"
    z=$(awk -v g=ramp_${CELL}_h1 '$1 == g { for (i = 1; i <= NF; i++) if ($i == "sdev_z") print $(i + 1) }' $src)
    awk -v z=${z:-0} 'BEGIN { exit !(z > 5) }' || flag "$src: ramp_${CELL}_h1 max sdev_z ${z:-none}, not > 5"
    for r in 1 2 3; do d=runs/ramp_${CELL}_h1_r$r
        [ -e $d/snap_900K.data ] || die "$d not finished"
        grep -q 'cutoff 3.8 components' $d/log.ramp && grep -q 'orientorder q4 0.6$' $d/log.ramp \
            && grep -q 'c_ncb>=4$' $d/log.ramp || die "$d: criterion is not 3.8/0.6/4"
    done
    ! compgen -G "runs/ramp_${CELL}_aniso_h1_r*" > /dev/null || die "runs/ramp_${CELL}_aniso_h1_r* exist"
    lo=$(( ${CI[$CELL]} * 3 )); hi=$(( lo + 2 ))
    # 1 K/ps: ~5 h on one A100 (610 ps at ~3 ns/day), within 24 h, so perc is fine (the 0.2 K/ps run is not).
    cmd=(sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --array=$lo-$hi --export=ALL,TAG=aniso
         submit_ramp.sh)
    cmp="python ../analysis/recryst_summary.py runs/ramp_${CELL}_h1_r* runs/ramp_${CELL}_aniso_h1_r*"
    ;;
  *) die "KIND must be prod, screen or ramp" ;;
esac
echo "${cmd[*]}  (EXTRA_VARS=$EXTRA_VARS)"
[ $DRY = 1 ] || "${cmd[@]}"
echo "compare afterwards: $cmp"
# Reading: the aniso group's sdev_z should drop to noise. If its t50 (anneals) is clearly shorter or its Tx (ramps)
# clearly lower, the iso box was holding growth back and the iso result for that composition is biased; then every
# composition needs the same barostat for the trend vs C. Cost: like the iso set (anneals up to ~40 h per run).

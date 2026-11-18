#!/bin/bash
# Isothermal anneal grid (RUNBOOK.md, recryst steps 3-4): for each Ta in TAS and each composition in CELLS, NREP
# replicas of submit_anneal.sh, with everything else from recryst/params/<MODEL_ID>.sh (criterion, BARO, XSTOP, MAX_NS, RUNTAG).
# A barostat variant sets BARO and RUNTAG together: BARO=iso RUNTAG=iso TAS="600 650" CELLS=x0 bash scripts/submit_grid.sh
#   Phase A (pilot, x0 over the grid):   CELLS=x0 bash scripts/submit_grid.sh [--dry-run]
#   Phase B (every composition):         bash scripts/submit_grid.sh [--dry-run]         (CELLS default: all five)
#   a subset of temperatures:            TAS="600 650" CELLS=x0 bash scripts/submit_grid.sh
# Run directories: runs/<MODEL_ID>/anneal_<cell>[_<RUNTAG>]_T<Ta>_r<rep> (submit_anneal.sh), so a (cell, Ta) whose
# runs exist is skipped: Phase B reuses Phase A's x0 runs, and nothing is submitted twice.
# Refuses a Ta that is not a calibration temperature (CALIB_TS: NUC, XC and GLASS exist only there) or not below
# TX_GUARD - 25 K (params: a Tx at a heating rate comparable to the anneal's 10 K/ps heat).
# Resources: NGPU perc A100-40GBs per run (params; 1 if unset) by default; RES="-A strachan -p a30 --gpus-per-node=2 --ntasks-per-node=2"
# for the A30s, RES="-A alta -p a100-80gb --constraint=K --gpus-per-node=2 --ntasks-per-node=2" for alta's k-nodes.
# Every submission is a separate go-ahead (RUNBOOK.md): run --dry-run first.
set -euo pipefail
tas=${TAS:-}                                # a TAS set here overrides recryst/params/<MODEL_ID>.sh
source "$(dirname "$(realpath "$0")")/common.sh"
TAS=${tas:-$TAS}
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
CELLS=${CELLS:-${CELLS_ALL[*]}}
RES=${RES:--A perc -p a100-40gb --gpus-per-node=${NGPU:-1} --ntasks-per-node=${NGPU:-1}}
for c in $CELLS; do [ -n "${CI[$c]:-}" ] || die "unknown cell $c (one of ${CELLS_ALL[*]})"; done
for TA in $TAS; do
    case " $CALIB_TS " in *" $TA "*) ;; *) die "TA $TA is not a calibration temperature ($CALIB_TS)" ;; esac
    [ $TA -lt $((TX_GUARD - 25)) ] || die "TA $TA is not below TX_GUARD $TX_GUARD - 25 K (recryst/params/$MODEL_ID.sh)"
done
unset TAG EXTRA_VARS                         # submit_anneal.sh reads both; take nothing from this shell
echo "$MODEL_ID: CELLS $CELLS; TAS $TAS; NREP $NREP; criterion $Q_RC/$Q_THR/$Q_NMIN; BARO $BARO; XSTOP $XSTOP;" \
     "MAX_NS $MAX_NS; RUNTAG '${RUNTAG}'"
for TA in $TAS; do
    arr=()
    for c in $CELLS; do
        if compgen -G "$RUNS/anneal_${c}${STEM}_T${TA}_r*" > /dev/null; then
            echo "T$TA $c: skip, $RUNS/anneal_${c}${STEM}_T${TA}_r* exist"; continue
        fi
        lo=$(( ${CI[$c]} * NREP )); arr+=("$lo-$(( lo + NREP - 1 ))")
    done
    [ ${#arr[@]} -gt 0 ] || continue
    cmd=(sbatch $RES --array=$(IFS=,; echo "${arr[*]}")
         --export=ALL,TA=$TA,NREP=$NREP,XSTOP=$XSTOP,MAX_NS=$MAX_NS,BARO=$BARO${RUNTAG:+,TAG=$RUNTAG} submit_anneal.sh)
    echo "T$TA: ${cmd[*]}"
    [ $DRY = 1 ] || "${cmd[@]}"
done
echo "analysis when they finish: [CELLS=...] bash scripts/analyze_grid.sh summary, then ... verdict"

#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -t 1-00:00:00
#SBATCH --job-name=cgst-anneal
#SBATCH --output=slurm-anneal-%A_%a.out
# Isothermal anneal (in.anneal) as a job array at one temperature TA, with automatic continuation.
#   sbatch --array=0-2 --export=ALL,TA=600 submit_anneal.sh                 # x0, replicas 1-3, at 600 K
#   sbatch --array=0-49 --export=ALL,TA=600,NREP=10 submit_anneal.sh        # 10 replicas of every cell
# Array index i -> cell CELLS[i / NREP], replica rep = i % NREP + 1 (with NREP 3, the mapping of
# meltquench/submit.sh). Replica rep starts from melt-quench glass ((rep - 1) % 3) + 1 with its own velocity seed, so
# beyond 3 replicas the glasses are reused: such replicas share the glass structure and differ in their dynamics.
# Run directory: runs/<MODEL_ID>/anneal_<cell>_T<TA>_r<rep>/, or .../anneal_<cell>_<TAG>_T<TA>_r<rep>/ with TAG set;
# the glass is meltquench/runs/<MODEL_ID>/<cell>_q<QRATE>_r<glass>/amorphous_300K.data (MODEL_ID: common/model.sh).
# Settings (--export=ALL,NAME=value): TA (K, required); NREP (replicas per cell, default 3); MAX_NS (hold length, ns)
# and XSTOP (fix halt level on xfracGST), both from recryst/params/<MODEL_ID>.sh unless set; MAXCHAIN (jobs per chain,
# default 4); EXTRA_VARS (extra LAMMPS -var options; not the criterion or barostat); TAG (optional run-name label for
# a variant of the same runs: same seeds and glasses, its own directories and replica group; required with a BARO
# other than the params' BARO_DEFAULT, e.g. --export=ALL,BARO=iso,TAG=iso; before _T so the
# analysis name patterns still match; scripts/submit_grid.sh passes RUNTAG). The criterion (Q_VARS), barostat (BARO)
# and glass rate (QRATE) come from recryst/params/<MODEL_ID>.sh, DT and MODEL from common/defaults.sh.
# Each task: exits if anneal_done.txt exists; as a continuation, stops the chain with an error if there is no newer
# restart than its predecessor started from (chain_progress.txt: the predecessor made no progress); otherwise
# records the newest restart, queues its own continuation (afterany, same array index) and runs, resuming from that
# restart. At most MAXCHAIN jobs per task. Old restart files are deleted (see prune below).
# The continuation inherits this job's account, partition, QoS, node constraint and GPU layout, so a chain started with command-line
# overrides (e.g. -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1) stays on those resources.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
TA=${TA:?set TA (K)}
NREP=${NREP:-3}
m=${MAX_NS:-}; x=${XSTOP:-}
source $ROOT/common/defaults.sh             # DT (same as the melt-quench), MODEL_ID, MODEL (per node type)
source $ROOT/recryst/params/$MODEL_ID.sh         # MAX_NS, XSTOP, BARO, QRATE, Q_VARS (calibrated criterion)
MAX_NS=${m:-$MAX_NS}; XSTOP=${x:-$XSTOP}
[ "$BARO" = "${BARO_DEFAULT:-$BARO}" ] || [ -n "${TAG:-}" ] || {   # a non-default barostat needs its own run directories
    echo "BARO=$BARO differs from the params default ${BARO_DEFAULT:-}: set TAG (RUNTAG in submit_grid.sh)" >&2; exit 1; }
[ -z "${NGPU:-}" ] || [ "$SLURM_NTASKS" = "$NGPU" ] || {
    echo "this job has $SLURM_NTASKS ranks, params NGPU=$NGPU: submit with --gpus-per-node=$NGPU --ntasks-per-node=$NGPU" >&2
    exit 1; }
: "${Q_VARS:?no calibrated criterion: run recryst/calib (submit.sh, then submit_calibrate.sh) for $MODEL_ID first}"
CHAIN=${CHAIN:-1}
MAXCHAIN=${MAXCHAIN:-4}
CELLS=(x0 x1 x2p5 x5 x10)
i=$SLURM_ARRAY_TASK_ID
cell=${CELLS[$((i / NREP))]}
rep=$((i % NREP + 1))
glass=$(((rep - 1) % 3 + 1))                # meltquench/submit.sh makes 3 glasses per cell
run=runs/$MODEL_ID/anneal_${cell}${TAG:+_$TAG}_T${TA}_r${rep}
src=$ROOT/meltquench/runs/$MODEL_ID/${cell}_q${QRATE}_r${glass}/amorphous_300K.data
[ -e $src ] || { echo "no glass $src (run meltquench/submit.sh with this MODEL_ID first)" >&2; exit 1; }
mkdir -p $run

cd $run
# Restart files (~2.6 MB each, one per 50 ps) are pruned: a finished run keeps only the newest (enough to extend the
# hold later); an unfinished one keeps the newest two (the newest may be truncated if a job died while writing it).
prune() { { ls anneal.*.restart 2>/dev/null || true; } | sort -t. -k2,2n | head -n -$1 | xargs -r rm -f; }
[ -e anneal_done.txt ] && { prune 1; echo "$run already done"; exit 0; }
prune 2
latest=$(ls anneal.*.restart 2>/dev/null | sort -t. -k2,2n | tail -1 || true)
# A continuation that finds no newer restart than the previous job started from means that job made no progress
# (e.g. a bad input): stop the chain here instead of queueing more jobs that would fail the same way.
if [ $CHAIN -gt 1 ] && [ "${latest:-none}" = "$(cat chain_progress.txt 2>/dev/null || echo none)" ]; then
    echo "$run: no new restart since the previous job (${latest:-none}); stopping the chain" >&2
    exit 1
fi
echo "${latest:-none}" > chain_progress.txt
if [ $CHAIN -lt $MAXCHAIN ]; then
    # keep the node type (e.g. --constraint=K on alta's a100-80gb: i-nodes there have no compiled model)
    feat=$(squeue -h -j $SLURM_JOB_ID -o %f 2>/dev/null | head -1); cons=""
    [ -n "$feat" ] && [ "$feat" != "(null)" ] && cons="--constraint=$feat"
    (cd $SLURM_SUBMIT_DIR && sbatch --array=$i --dependency=afterany:${SLURM_ARRAY_JOB_ID}_${i} \
        -A $SLURM_JOB_ACCOUNT -p $SLURM_JOB_PARTITION --qos=$SLURM_JOB_QOS $cons \
        --gpus-per-node=$SLURM_GPUS_ON_NODE --ntasks-per-node=$SLURM_NTASKS_PER_NODE \
        --export=ALL,TA=$TA,NREP=$NREP,MAX_NS=$MAX_NS,XSTOP=$XSTOP,DT=$DT,CHAIN=$((CHAIN + 1)),MAXCHAIN=$MAXCHAIN \
        submit_anneal.sh)
fi
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/recryst/in.anneal -log log.anneal.$CHAIN \
    -var root $ROOT -var cell $cell -var rep $rep -var seed $((30011 * (i + 1) + TA)) -var Ta $TA \
    -var src $src \
    -var max_ns $MAX_NS -var dt $DT -var resume $([ -n "$latest" ] && echo 1 || echo 0) -var rfile ${latest:-none} \
    -var xstop $XSTOP -var model $MODEL -var baro $BARO $Q_VARS ${EXTRA_VARS:-}
if [ -e anneal_done.txt ]; then prune 1; fi

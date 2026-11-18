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
#SBATCH --job-name=cgst-ramp
#SBATCH --output=slurm-ramp-%A_%a.out
# Heating-ramp crystallization (in.ramp) as a job array over the melt-quench samples (10 K/ps quench).
#   x0 r1 at HRATE (recryst/params/<MODEL_ID>.sh, 0.2 K/ps):  sbatch --array=0 submit_ramp.sh
#     (0.2 K/ps to 900 K is 3,010 ps: ~28 h at 444 on 2 A100s, so it runs as a chain of jobs, see below)
#   more replicas or compositions: --array=1,2 (x0 r2, r3), 3-5 (x1), ...
# Array index i -> cell CELLS[i / 3], replica i % 3 + 1 (same mapping as meltquench/submit.sh).
# Run directory: runs/<MODEL_ID>/ramp_<cell>_h<HRATE>_r<rep>/, or .../ramp_<cell>_<TAG>_h<HRATE>_r<rep>/ with TAG
# set; the glass is meltquench/runs/<MODEL_ID>/<cell>_q<QRATE>_r<rep>/amorphous_300K.data (MODEL_ID: common/model.sh).
# Criterion (Q_VARS), barostat (BARO), TMAX and QRATE come from recryst/params/<MODEL_ID>.sh.
# Settings (--export=ALL,NAME=value): HRATE (K/ps; overrides recryst/params/<MODEL_ID>.sh); EXTRA_VARS (extra LAMMPS -var options;
# not the criterion or barostat, which are passed already); TAG (optional run-name label for a variant of the same
# runs, same seeds and glasses); MAXCHAIN (jobs per ramp, default 3); DT and MODEL come from common/defaults.sh.
# Continuation, as in submit_anneal.sh: each task exits if ramp_done.txt exists; otherwise it resumes from the newest
# ramp.<T>K.restart (written at every 50 K boundary by in.ramp), first queueing its own continuation (afterany, same
# array index, the same account/partition/QoS/constraint/GPU layout) unless MAXCHAIN is reached; a continuation that finds no
# newer restart than its predecessor started from stops the chain (chain_progress.txt). Old restart files are pruned
# (the newest two are kept while running, the newest one when done). Job N > 1 logs to log.ramp.<N>.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
hr=${HRATE:-}
source $ROOT/common/defaults.sh             # DT (same as the melt-quench), MODEL_ID, MODEL (per node type)
source $ROOT/recryst/params/$MODEL_ID.sh         # HRATE, TMAX, QRATE (which glasses), Q_VARS (calibrated criterion)
HRATE=${hr:-$HRATE}
[ -z "${NGPU:-}" ] || [ "$SLURM_NTASKS" = "$NGPU" ] || {
    echo "this job has $SLURM_NTASKS ranks, params NGPU=$NGPU: submit with --gpus-per-node=$NGPU --ntasks-per-node=$NGPU" >&2
    exit 1; }
: "${Q_VARS:?no calibrated criterion: run recryst/calib (submit.sh, then submit_calibrate.sh) for $MODEL_ID first}"
CELLS=(x0 x1 x2p5 x5 x10)
i=$SLURM_ARRAY_TASK_ID
cell=${CELLS[$((i / 3))]}
rep=$((i % 3 + 1))
run=runs/$MODEL_ID/ramp_${cell}${TAG:+_$TAG}_h${HRATE}_r${rep}
src=$ROOT/meltquench/runs/$MODEL_ID/${cell}_q${QRATE}_r${rep}/amorphous_300K.data
[ -e $src ] || { echo "no glass $src (run meltquench/submit.sh with this MODEL_ID first)" >&2; exit 1; }
CHAIN=${CHAIN:-1}
MAXCHAIN=${MAXCHAIN:-3}
mkdir -p $run && cd $run
prune() { { ls ramp.*K.restart 2>/dev/null || true; } | sort -t. -k2,2n | head -n -$1 | xargs -r rm -f; }
[ -e ramp_done.txt ] && { prune 1; echo "$run already done"; exit 0; }
prune 2
latest=$(ls ramp.*K.restart 2>/dev/null | sort -t. -k2,2n | tail -1 || true)
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
        --export=ALL,HRATE=$HRATE,DT=$DT,CHAIN=$((CHAIN + 1)),MAXCHAIN=$MAXCHAIN submit_ramp.sh)
fi
if [ -n "$latest" ]; then
    t0=${latest#ramp.}; t0=${t0%K.restart}
    resume="-var resume 1 -var rfile $latest -var tstart $t0"
else
    resume=""
fi
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/recryst/in.ramp -log log.ramp$([ $CHAIN -gt 1 ] && echo .$CHAIN) \
    -var root $ROOT -var cell $cell -var rep $rep -var seed $((20011 * (i + 1))) -var hrate $HRATE -var dt $DT \
    -var model $MODEL -var src $src -var tmax $TMAX -var baro $BARO $Q_VARS $resume \
    ${EXTRA_VARS:-}
if [ -e ramp_done.txt ]; then prune 1; fi

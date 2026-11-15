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
#SBATCH --job-name=cgst-mq
#SBATCH --output=slurm-%A_%a.out
# Melt-quench production as a job array: one task per (cell, replica) at quench rate QRATE.
#   all cells x 3 replicas:            sbatch --array=0-14 submit.sh
#   1 K/ps sensitivity (x0, x10, r1):  sbatch --array=0,12 --export=ALL,QRATE=1 submit.sh
#   longer melt hold for every run (after an MSD-gate ERROR): --export=ALL,HOLD_PS=150
#   444 on 3 A30s (24 GB each):       sbatch --constraint=B --gpus-per-node=3 --ntasks-per-node=3 --export=ALL,NGPU=3 ...
# SIZE, NGPU (checked against the job's ranks), QRATE, HOLD_PS and TMELT come from meltquench/params/<MODEL_ID>.sh;
# QRATE and HOLD_PS set in the environment override it, and NGPU too where the params allow (NGPU=${NGPU:-2}).
# Array index i -> cell CELLS[i / 3], replica r = i % 3 + 1.
# Run directory: runs/<MODEL_ID>/<cell>_q<QRATE>_r<r>/ (MODEL_ID: common/model.sh).
# Velocity seed = 10007*(i+1) + QRATE, so every run has a different seed.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
q=${QRATE:-}; h=${HOLD_PS:-}
source $ROOT/common/defaults.sh             # DT, MODEL_ID, MODEL (per node type)
source $ROOT/meltquench/params/$MODEL_ID.sh # SIZE, TMELT, QRATE, HOLD_PS (keep HOLD_PS the same for every run compared)
QRATE=${q:-$QRATE}; HOLD_PS=${h:-$HOLD_PS}
[ -z "${NGPU:-}" ] || [ "$SLURM_NTASKS" = "$NGPU" ] || {
    echo "this job has $SLURM_NTASKS ranks, params NGPU=$NGPU: submit with --gpus-per-node=$NGPU --ntasks-per-node=$NGPU" >&2
    exit 1; }
[ -e $ROOT/structures/$SIZE/x0.data ] || { echo "no structures/$SIZE/: python structures/build_supercells.py --nrep ${SIZE:0:1}" >&2; exit 1; }
CELLS=(x0 x1 x2p5 x5 x10)
i=$SLURM_ARRAY_TASK_ID
cell=${CELLS[$((i / 3))]}
rep=$((i % 3 + 1))
run=runs/$MODEL_ID/${cell}_q${QRATE}_r${rep}
mkdir -p $run && cd $run
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/meltquench/in.meltquench -log log.mq \
    -var root $ROOT -var cell $cell -var seed $((10007 * (i + 1) + QRATE)) -var qrate $QRATE -var dt $DT \
    -var model $MODEL -var hold_ps $HOLD_PS -var tmelt $TMELT -var size $SIZE

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
#   10 K/ps, all cells x 3 replicas:   sbatch --array=0-14 submit.sh
#   1 K/ps sensitivity (x0, x10, r1):  sbatch --array=0,12 --export=ALL,QRATE=1 submit.sh
#   longer 1500 K hold for every run (after an MSD-gate ERROR): --export=ALL,HOLD_PS=150
# Array index i -> cell CELLS[i / 3], replica r = i % 3 + 1. Run directory: runs/<cell>_q<QRATE>_r<r>/
# Velocity seed = 10007*(i+1) + QRATE, so every run has a different seed.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
QRATE=${QRATE:-10}
HOLD_PS=${HOLD_PS:-100}                     # 1500 K hold; keep it the same for every run that is compared
source $ROOT/common/defaults.sh             # DT, MODEL (per node type)
CELLS=(x0 x1 x2p5 x5 x10)
i=$SLURM_ARRAY_TASK_ID
cell=${CELLS[$((i / 3))]}
rep=$((i % 3 + 1))
run=runs/${cell}_q${QRATE}_r${rep}
mkdir -p $run && cd $run
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/meltquench/in.meltquench -log log.mq \
    -var root $ROOT -var cell $cell -var seed $((10007 * (i + 1) + QRATE)) -var qrate $QRATE -var dt $DT \
    -var model $MODEL -var hold_ps $HOLD_PS

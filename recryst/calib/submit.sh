#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -t 02:00:00
#SBATCH --job-name=cgst-calib
#SBATCH --output=slurm-calib-%A_%a.out
# Crystallinity calibration references (in.calib), one array task per (state, T):
#   tasks  0-23: rocksalt crystal x0 x1 x2p5 x5 (structures/333, minimized) at 300 500 550 600 650 700 K
#   tasks 24-53: amorphous x0 x1 x2p5 x5 x10 (meltquench/runs/<MODEL_ID>/<cell>_q10_r1) at the same temperatures
# (550-650 K are the planned anneal temperatures, so XSTOP and --x-crystal come from references at Ta.)
# x10 rocksalt is excluded: it disorders within ps at 600 K (tests/RESULTS.md, 1a), so it is not a crystal reference.
#   sbatch --array=0-53 submit.sh     (after the 10 K/ps melt-quench runs exist); then
#   sbatch submit_calibrate.sh        (calibrate.py in the cgst-ana env; writes calibrate.out)
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
source $ROOT/common/defaults.sh             # DT, MODEL_ID, MODEL (per node type)
source $ROOT/params/$MODEL_ID.sh            # QRATE (which glasses)
mkdir -p $MODEL_ID && cd $MODEL_ID          # outputs per model: calib/<MODEL_ID>/
TS=(300 500 550 600 650 700)
NT=${#TS[@]}
i=$SLURM_ARRAY_TASK_ID
if [ $i -lt $((4 * NT)) ]; then
    CELLS=(x0 x1 x2p5 x5); cell=${CELLS[$((i / NT))]}; T=${TS[$((i % NT))]}
    src=$ROOT/structures/333/$cell.data; tag=crys_${cell}_${T}K; mini=1
else
    j=$((i - 4 * NT)); CELLS=(x0 x1 x2p5 x5 x10); cell=${CELLS[$((j / NT))]}; T=${TS[$((j % NT))]}
    src=$ROOT/meltquench/runs/$MODEL_ID/${cell}_q${QRATE}_r1/amorphous_300K.data; tag=amor_${cell}_${T}K; mini=0
fi
$ROOT/common/run_lmp.sh 1 -in ../in.calib -log log.$tag -var root $ROOT -var src $src -var T $T -var tag $tag \
    -var seed $((40009 * (i + 1))) -var dt $DT -var minimize $mini -var model $MODEL

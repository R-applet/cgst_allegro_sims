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
#   1 K/ps, all cells x 3 replicas:   sbatch --array=0-14 submit_ramp.sh
#   0.2 K/ps rate check, x0 r1:       sbatch --array=0 --export=ALL,HRATE=0.2 submit_ramp.sh
#     (3,010 ps: ~21.6 h on these 2 A30s; on one A100 it would exceed the 24 h limit, and there is no restart)
# Array index i -> cell CELLS[i / 3], replica i % 3 + 1 (same mapping as meltquench/submit.sh).
# Run directory: runs/ramp_<cell>_h<HRATE>_r<rep>/, or runs/ramp_<cell>_<TAG>_h<HRATE>_r<rep>/ with TAG set.
# Settings (--export=ALL,NAME=value): HRATE (K/ps, default 1); EXTRA_VARS (extra LAMMPS -var options, e.g. the
# calibrated q_rc/q_thr/q_nmin or -var baro aniso); TAG (optional run-name label for a variant of the same runs, e.g.
# TAG=aniso, same seeds and glasses); DT and MODEL come from common/defaults.sh.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
HRATE=${HRATE:-1}
source $ROOT/common/defaults.sh             # DT (same as the melt-quench), MODEL (per node type)
CELLS=(x0 x1 x2p5 x5 x10)
i=$SLURM_ARRAY_TASK_ID
cell=${CELLS[$((i / 3))]}
rep=$((i % 3 + 1))
run=runs/ramp_${cell}${TAG:+_$TAG}_h${HRATE}_r${rep}
mkdir -p $run && cd $run
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/recryst/in.ramp -log log.ramp \
    -var root $ROOT -var cell $cell -var rep $rep -var seed $((20011 * (i + 1))) -var hrate $HRATE -var dt $DT \
    -var model $MODEL \
    ${EXTRA_VARS:-}

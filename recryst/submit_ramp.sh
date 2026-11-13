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
#     (0.2 K/ps to 900 K is 3,010 ps: ~18 h on these 2 A30s; on one A100 it can exceed the 24 h limit, no restart)
#   more replicas or compositions: --array=1,2 (x0 r2, r3), 3-5 (x1), ...
# The 1 K/ps ramps of run5_ep301 crystallized nothing by 900 K, so they are not part of the workflow (RUNBOOK.md).
# Array index i -> cell CELLS[i / 3], replica i % 3 + 1 (same mapping as meltquench/submit.sh).
# Run directory: runs/<MODEL_ID>/ramp_<cell>_h<HRATE>_r<rep>/, or .../ramp_<cell>_<TAG>_h<HRATE>_r<rep>/ with TAG
# set; the glass is meltquench/runs/<MODEL_ID>/<cell>_q<QRATE>_r<rep>/amorphous_300K.data (MODEL_ID: common/model.sh).
# Criterion (Q_VARS), barostat (BARO), TMAX and QRATE come from recryst/params/<MODEL_ID>.sh.
# Settings (--export=ALL,NAME=value): HRATE (K/ps; overrides recryst/params/<MODEL_ID>.sh); EXTRA_VARS (extra LAMMPS -var options;
# not the criterion or barostat, which are passed already); TAG (optional run-name label for a variant of the same
# runs, same seeds and glasses); DT and MODEL come from common/defaults.sh.
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
mkdir -p $run && cd $run
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/recryst/in.ramp -log log.ramp \
    -var root $ROOT -var cell $cell -var rep $rep -var seed $((20011 * (i + 1))) -var hrate $HRATE -var dt $DT \
    -var model $MODEL -var src $src -var tmax $TMAX -var baro $BARO $Q_VARS \
    ${EXTRA_VARS:-}

#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 04:00:00
#SBATCH --job-name=cgst-phases
#SBATCH --output=slurm-%A_%a.out
# 300 K NVT runs of the DFT-sized phase cells (in.phases) as a job array, one GPU per task (144-160 atoms).
#   pilot (am_c10 r1, hex_c1 r1):   sbatch --array=9,21 submit.sh
#   everything (8 phases x 3):      sbatch --array=0-23 submit.sh
#   on perc instead of strachan:     sbatch -A perc -p a100-40gb --array=... submit.sh
# PHASES, NREP, TEMP, DT, EQ_PS, PROD_PS and TDAMP_PS come from phases/params/<MODEL_ID>.sh (DT there overrides
# the model's production DT). Array index i -> phase PHASES[i / NREP], replica r = i % NREP + 1.
# Run directory: runs/<MODEL_ID>/<phase>_r<r>/ (MODEL_ID: common/model.sh). Velocity seed = 1009*(i+1) + 7.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
source $ROOT/common/defaults.sh                 # MODEL_ID, MODEL (per node type)
source $ROOT/phases/params/$MODEL_ID.sh         # PHASES, NREP, TEMP, DT, EQ_PS, PROD_PS, TDAMP_PS
i=$SLURM_ARRAY_TASK_ID
[ $i -lt $(( ${#PHASES[@]} * NREP )) ] || { echo "array index $i > $(( ${#PHASES[@]} * NREP - 1 ))" >&2; exit 1; }
phase=${PHASES[$((i / NREP))]}
rep=$((i % NREP + 1))
run=runs/$MODEL_ID/${phase}_r${rep}
mkdir -p $run && cd $run
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/phases/in.phases -log log.phases \
    -var root $ROOT -var phase $phase -var seed $((1009 * (i + 1) + 7)) -var model $MODEL -var dt $DT \
    -var temp $TEMP -var eq_ps $EQ_PS -var prod_ps $PROD_PS -var tdamp_ps $TDAMP_PS

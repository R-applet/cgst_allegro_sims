#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -t 01:00:00
#SBATCH --job-name=cgst-calibrate
#SBATCH --output=slurm-calibrate-%j.out
# Calibration step 2-4 (recryst/README.md): the Q4 criterion scan on the in.calib references (submit.sh), in the
# cgst-ana env (needs matplotlib for calib.png). CPU only; Gilbreth has no CPU partition, so it takes one A30.
# Writes calibrate.out, calib_scan.csv and calib.png in calib/<MODEL_ID>/, next to submit.sh's references.
#   sbatch submit_calibrate.sh        (after submit.sh's array has finished)
#   sbatch --export=ALL,CALIB_ARGS="--choose 3.8 0.6 4" submit_calibrate.sh   (report a chosen criterion)
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
source $ROOT/common/model.sh                # MODEL_ID
cd $MODEL_ID
$ROOT/env/cgst-ana/bin/python ../calibrate.py --crystal crys_*.lammpstrj.gz --amorphous amor_*.lammpstrj.gz \
    ${CALIB_ARGS:-} > calibrate.out 2>&1

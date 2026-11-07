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
#SBATCH --job-name=cgst-density
# Test 1g: crystal density at 300 K with the production model (x0 rocksalt, 12447 atoms).
# Compare with the amorphous V/atom from the reference melt-quench (same model, epoch 301): see tests/RESULTS.md.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
source $ROOT/common/defaults.sh
$ROOT/common/run_lmp.sh 1 -in in.density -log log.density_x0_300K -var cell x0 -var T 300 -var dt $DT
cat density_*.txt | tee RESULT.txt

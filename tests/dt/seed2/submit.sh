#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -t 03:00:00
#SBATCH --job-name=cgst-dt2
# Test 1c repeat: second velocity seed and 40 ps NVE per dt (same state and thresholds as tests/dt).
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../../..)
$ROOT/common/run_lmp.sh 1 -in ../in.dt -log log.dt -var root $ROOT -var seed 9020211 -var nve_ps 40
python3 ../analyze_dt.py $PWD | tee RESULT.txt

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
#SBATCH --job-name=cgst-dt
# Test 1c: NVE energy conservation at dt = 0.5/1/2 fs in 1500 K liquid x10 (4096 atoms, 1 A30).
cd $SLURM_SUBMIT_DIR
../../common/run_lmp.sh 1 -in in.dt -log log.dt || exit 1
python3 analyze_dt.py | tee RESULT.txt

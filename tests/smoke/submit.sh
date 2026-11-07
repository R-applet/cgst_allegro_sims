#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 00:30:00
#SBATCH --job-name=cgst-smoke
# Test 1a: smoke test of the model and the shared includes on the 512-site x0 and x10 cells (1 A30).
cd $SLURM_SUBMIT_DIR
for cell in x0 x10; do
    ../../common/run_lmp.sh 1 -in in.smoke -log log.smoke_$cell -var cell $cell || echo "FAILED: $cell"
done
python3 check_smoke.py

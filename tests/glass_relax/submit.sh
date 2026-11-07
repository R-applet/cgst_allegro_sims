#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --constraint=N
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 03:00:00
#SBATCH --job-name=cgst-glassrelax
# Check 1 after 1h: do DFT glasses (about 5.8 g/cc) collapse toward the model's 6.29 g/cc glass when relaxed with the
# model at NPT 300 K, 0 bar? Crystal frames are the control. Uses the model recompiled on an a100-40gb n-node
# (tests/a100_model), so it is pinned to --constraint=N. Verdict -> RESULT.txt (analyze.py)
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
module load cuda/12.6.0
apptainer exec --bind /depot,/scratch /depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif python prep.py || exit 1
$ROOT/common/run_lmp.sh 1 -in in.relax -log log.relax -var root $ROOT -var frames "$(cat frames.txt)" \
    -var model $ROOT/tests/a100_model/run5_ep301.N.nequip.pt2 > screen.txt 2>&1 || echo "LAMMPS FAILED (screen.txt)"
python3 analyze.py | tee RESULT.txt
apptainer exec --bind /depot,/scratch /depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif python to_xyz.py

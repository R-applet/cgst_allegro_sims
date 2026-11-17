#!/bin/sh -l
#SBATCH -A strachan
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --tasks-per-node=32
#SBATCH -t 04:00:00
#SBATCH -q normal
#SBATCH --job-name=gst_dimer
# Usage: sbatch run_dirs.sh atoms            (all isolated atoms)
#        sbatch run_dirs.sh dimers/Ge-Te     (every r_* point for one pair)
# Finished points (OUTCAR with "General timing") are skipped, so resubmit to continue.

module load gcc/12.2.0 openmpi/4.1.4
module load vasp/6.4.1

cd $SLURM_SUBMIT_DIR
TARGET=$1

for d in $(ls -d $TARGET/*/ | sort); do
    if grep -qs "General timing" $d/OUTCAR; then continue; fi
    echo "+++ $d start `date`"
    (cd $d && mpirun -np $SLURM_NTASKS vasp_std > outVASP)
    grep -qs "General timing" $d/OUTCAR || echo "!!! $d did not finish, see $d/outVASP"
    echo "+++ $d end   `date`"
done


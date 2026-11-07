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
#SBATCH --job-name=cgst-container
# Test 1f: lammps_debug.sif vs lammps_stable.sif through the production launch path (common/run_lmp.sh: srun, one
# rank per GPU), with only SIF changed. Starting the containers without srun is not an option inside a batch job:
# Open MPI sees the Slurm environment, assumes srun direct launch, and aborts in MPI_Init (job 12235379).
#   energies: in.model_check on the model_check frames, in frames_<sif>/ (symlinked frames; nothing is written to
#             tests/model_check) -> frames_<sif>/lammps_energies.txt, log in frames_<sif>/log.model_check
#   speed:    ../scaling/in.bench (13824 atoms, ana=1), run here -> log.bench_<sif>
# Pass: stable starts, and its energies match debug's to 1e-6 eV/atom. Speeds are recorded. Verdict -> RESULT.txt
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
MC=$ROOT/tests/model_check
: > failures.txt
for s in debug stable; do
    export SIF=/depot/prism/data/rushik/lammps_wallegro/lammps_$s.sif
    mkdir -p frames_$s && ln -sf $MC/frame_*.data frames_$s/
    (cd frames_$s && $ROOT/common/run_lmp.sh 1 -in $MC/in.model_check -log log.model_check -var root $ROOT \
        -var frames "$(cat $MC/frames.txt)" > screen.txt 2>&1) || echo "FAILED energies: $s (frames_$s/screen.txt)" >> failures.txt
    $ROOT/common/run_lmp.sh 1 -in ../scaling/in.bench -log log.bench_$s -var ana 1 -var tag cont_$s \
        > screen_bench_$s.txt 2>&1 || echo "FAILED bench: $s (screen_bench_$s.txt)" >> failures.txt
done
{
    cat failures.txt
    python3 $MC/compare_energies.py frames_debug/lammps_energies.txt frames_stable/lammps_energies.txt
    for s in debug stable; do
        p=$(grep "^Performance:" log.bench_$s 2>/dev/null | sed -n 2p); echo "$s bench: ${p:-no timed run}"
    done
} | tee RESULT.txt

#!/bin/bash
# Run LAMMPS (Kokkos/CUDA, pair allegro) inside the project container, one MPI rank per GPU.
# Usage (inside a Slurm allocation):  common/run_lmp.sh NGPU -in in.file -log log.file [-var name value ...]
#
# Container: lammps_debug.sif = LAMMPS 30 Mar 2026, Kokkos 5.0.2 (CUDA, double), libtorch 2.8.0+cu126.
# The model in models/ is compiled for sm_80 GPUs but was built on an A30 b-node, and it crashes in the model loader on
# every A100 node tried so far (Illegal instruction). Use partition a30 until tests/a100_model reports.
# Which nodes and containers have been tested, with results: tests/RESULTS.md (environment probe, 1d, 1f).
# SIF can be overridden from the environment (tests/container uses this for lammps_stable.sif).
set -euo pipefail
NGPU=$1; shift
SIF=${SIF:-/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif}
module load cuda/12.6.0 >/dev/null 2>&1 || true
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
# Slurm can raise CPUs/task above the request (e.g. to cover --mem), leaving SLURM_CPUS_PER_TASK and
# SLURM_TRES_PER_TASK inconsistent, which makes srun abort. Drop the latter and pass the count explicitly.
unset SLURM_TRES_PER_TASK
srun --ntasks=$NGPU --cpus-per-task=$OMP_NUM_THREADS apptainer run --nv --bind /depot,/scratch --env OMP_NUM_THREADS=$OMP_NUM_THREADS $SIF \
    -k on g $NGPU -sf kk -pk kokkos newton on neigh half "$@"

#!/bin/bash
# Run LAMMPS (Kokkos/CUDA, pair allegro) inside the project container, one MPI rank per GPU.
# Usage (inside a Slurm allocation):  common/run_lmp.sh NGPU -in in.file -log log.file [-var name value ...]
# Before starting, it records the input, its includes, the command and the provenance in lmp_inputs/<log>/
# (common/record_inputs.sh), for human reference.
#
# Container: lammps_debug.sif = LAMMPS 30 Mar 2026, Kokkos 5.0.2 (CUDA, double), libtorch 2.8.0+cu126.
# The compiled model must match the node's CPU: common/defaults.sh sets MODEL per node type (a30 b/d, a100-40gb g/n, a100-80gb k),
# and inputs take it as -var model $MODEL (models/provenance.md).
# Which nodes and containers have been tested: tests/RESULTS.md (Environment; 1f).
# The container is $SIF from common/model.sh; it can be overridden from the environment (tests/container uses this
# for lammps_stable.sif).
set -euo pipefail
NGPU=$1; shift
source "$(dirname "$(realpath "$0")")/model.sh"
module load cuda/12.6.0 >/dev/null 2>&1 || true
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
# Slurm can raise CPUs/task above the request (e.g. to cover --mem), leaving SLURM_CPUS_PER_TASK and
# SLURM_TRES_PER_TASK inconsistent, which makes srun abort. Drop the latter and pass the count explicitly.
unset SLURM_TRES_PER_TASK
# reference copy of the input, its includes, the command and the provenance (lmp_inputs/<log>/; never stops a run)
source "$(dirname "$(realpath "$0")")/record_inputs.sh"
record_inputs $NGPU "$@" || echo "run_lmp.sh: could not record the inputs (lmp_inputs/); running anyway" >&2
# exec: bash never reads this file again once LAMMPS starts, so editing it during a run cannot break the job (bash
# reads scripts as it goes; an edit during job 12359216_0 made it fail with a syntax error after LAMMPS had finished).
exec srun --ntasks=$NGPU --cpus-per-task=$OMP_NUM_THREADS apptainer run --nv --bind /depot,/scratch --env OMP_NUM_THREADS=$OMP_NUM_THREADS $SIF \
    -k on g $NGPU -sf kk -pk kokkos newton on neigh half "$@"

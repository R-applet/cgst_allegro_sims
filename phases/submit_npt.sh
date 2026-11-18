#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 02:00:00
#SBATCH --job-name=cgst-phases-npt
#SBATCH --output=slurm-npt-%A_%a.out
# 300 K, 0 bar NPT runs of the C-free DFT phase cells (in.npt) as a job array, one GPU per task (144 atoms, ~12 min
# for 500 ps on an A100).
#   everything (3 phases x 3 seeds):   sbatch --array=0-8 --export=ALL,MODEL_ID=<id>,PMIX_MCA_gds=hash submit_npt.sh
# NPT_PHASES, NREP, TEMP, DT, NPT_PS, TDAMP_PS and PDAMP_PS come from phases/params/<MODEL_ID>.sh. Array index i ->
# phase NPT_PHASES[i / NREP], replica r = i % NREP + 1; barostat iso for am_* cells, tri for the crystals. Velocity
# seed = that of the NVT run of the same phase and replica (submit.sh: 1009 (k + 1) + 7, k its NVT array index).
# Run directory: runs/<MODEL_ID>/npt/<phase>_r<r>/. Analysis: analysis/phases_npt.py (phases/README.md).
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
source $ROOT/common/defaults.sh                 # MODEL_ID, MODEL (per node type)
source $ROOT/phases/params/$MODEL_ID.sh         # PHASES, NPT_PHASES, NREP, TEMP, DT, NPT_PS, TDAMP_PS, PDAMP_PS
i=$SLURM_ARRAY_TASK_ID
[ $i -lt $(( ${#NPT_PHASES[@]} * NREP )) ] || { echo "array index $i > $(( ${#NPT_PHASES[@]} * NREP - 1 ))" >&2; exit 1; }
phase=${NPT_PHASES[$((i / NREP))]}
rep=$((i % NREP + 1))
p=-1; for k in "${!PHASES[@]}"; do [ "${PHASES[$k]}" = "$phase" ] && p=$k; done
[ $p -ge 0 ] || { echo "$phase is not in PHASES" >&2; exit 1; }
case $phase in am_*) baro=iso ;; *) baro=tri ;; esac
run=runs/$MODEL_ID/npt/${phase}_r${rep}
mkdir -p $run && cd $run
$ROOT/common/run_lmp.sh $SLURM_NTASKS -in $ROOT/phases/in.npt -log log.npt \
    -var root $ROOT -var phase $phase -var seed $((1009 * (p * NREP + rep) + 7)) -var model $MODEL -var dt $DT \
    -var temp $TEMP -var run_ps $NPT_PS -var tdamp_ps $TDAMP_PS -var pdamp_ps $PDAMP_PS -var baro $baro

#!/bin/bash -l
#SBATCH -A perc
#SBATCH --partition=a100-40gb
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH -t 04:00:00
#SBATCH --job-name=cgst-phases-ana
#SBATCH --output=slurm-analysis-%j.out
# Analysis of the phases runs (analysis/phases_compare.py; CPU only, the GPU is the partition's minimum):
#   sbatch submit_analysis.sh                     every finished run in runs/<MODEL_ID>/ without analysis/, then compare
#   sbatch --export=ALL,REDO=1 submit_analysis.sh  every finished run
# Four runs at a time, 4 OpenMP threads each for DoSPT. Runs listed in EXACT_V (default: the two pilot runs) also get
# the DoSPT spectrum from the dumped velocities (the check of DoSPT's estimated velocities). Then dft-check on the
# hex_gst DFT trajectory with every 10th frame (the validation of the RDF/ADF definitions), and compare.
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ..)
source $ROOT/common/model.sh
PY=$ROOT/env/cgst-ana/bin/python
EXACT_V=${EXACT_V:-"am_c10_r1 hex_c1_r1"}
export SLURM_CPUS_PER_TASK=4 TMPDIR=${TMPDIR:-/tmp}
todo=()
for r in runs/$MODEL_ID/*_r*; do
    grep -q "phases: .* done" $r/log.phases 2>/dev/null || { echo "skip $r: not finished"; continue; }
    [ -n "${REDO:-}" ] || [ ! -e $r/analysis/vdos_species.txt ] && todo+=($r)
done
echo "analysing ${#todo[@]} runs"
printf '%s\n' "${todo[@]}" | xargs -P 4 -I{} sh -c \
    'n=$(basename {}); case " '"$EXACT_V"' " in *" $n "*) x=--exact-v ;; *) x= ;; esac; '"$PY $ROOT"'/analysis/phases_compare.py analyze {} $x'
$PY $ROOT/analysis/phases_compare.py dft-check $DFT_PHASES/../../../dospt_example/traj.xyz --phase hex_gst --every 10
MODEL_ID=$MODEL_ID $PY $ROOT/analysis/phases_compare.py compare

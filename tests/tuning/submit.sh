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
#SBATCH --job-name=cgst-tuning
# Item 8: ghost cutoff 7.5 (current) vs 7.0 (= 6.0 force cutoff + 1.0 skin): speed, and whether the 6 A RDF still runs.
# Item 10: PMIx/munge noise lines in the screen output, default vs PMIX_MCA_psec=native.
# Verdict -> RESULT.txt
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
source $ROOT/common/defaults.sh             # MODEL (per node type)
for cc in 7.5 7.0; do
    $ROOT/common/run_lmp.sh 1 -in in.commcut -log log.cc$cc -var cc $cc -var model $MODEL > screen_cc$cc.txt 2>&1 || echo "FAILED cc=$cc" >> failures.txt
done
PMIX_MCA_psec=native $ROOT/common/run_lmp.sh 1 -in in.commcut -log log.pmix -var cc 7.5 -var model $MODEL > screen_pmix.txt 2>&1 \
    || echo "FAILED pmix run" >> failures.txt
{
    cat failures.txt 2>/dev/null
    for cc in 7.5 7.0; do
        p=$(grep "^Performance:" log.cc$cc 2>/dev/null | sed -n 2p)
        rows=$(awk 'NF==24' rdf_cc$cc.dat 2>/dev/null | wc -l)
        echo "cc=$cc: ${p:-no timed run}; RDF rows: $rows; ghosts: $(grep -m1 '^Nghost' log.cc$cc | awk '{print $3}')"
    done
    echo "munge/PMIx noise lines: default $(grep -c -i 'munge\|PMIX ERROR' screen_cc7.5.txt), PMIX_MCA_psec=native $(grep -c -i 'munge\|PMIX ERROR' screen_pmix.txt)"
} | tee RESULT.txt

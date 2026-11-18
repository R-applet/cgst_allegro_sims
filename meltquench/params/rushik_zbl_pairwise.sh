# Melt-quench design numbers for MODEL_ID=rushik_zbl_pairwise, each with where it came from. Sourced by meltquench/submit.sh.
# PROVISIONAL (2026-11-18): copied from nequip_no_zbl.sh so the potentials' runs differ only in the model. TMELT and
# HOLD_PS stay provisional until this model's superheating pilot, x0 r1 and x10 r1 (sbatch --array=0,12), confirms
# them (RUNBOOK.md, meltquench step 1); the pilot runs are production runs (same seeds as nequip_no_zbl's).

SIZE=444            # supercell, as nequip_no_zbl (structures/444/, 29.5k-32.8k atoms, 96.5 A box), so the glasses compare
                    #   cell for cell
NGPU=${NGPU:-2}     # GPUs (= MPI ranks) per run, as nequip_no_zbl; a submission may set another value, e.g.
                    #   --export=ALL,NGPU=3 on 3 A30s
TMELT=1500          # K, PROVISIONAL: nequip_no_zbl's (Tm_app 1139 K x0, 983 K x10). To confirm from the pilot's Tm_app
                    #   and closest approach in the 1500 K liquid
HOLD_PS=100         # ps at TMELT, PROVISIONAL: nequip_no_zbl's (MSD gate 100 A^2). To confirm from the pilot's MSD
QRATE=10            # K/ps, as nequip_no_zbl

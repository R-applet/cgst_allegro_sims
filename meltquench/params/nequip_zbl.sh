# Melt-quench design numbers for MODEL_ID=nequip_zbl, each with where it came from. Sourced by meltquench/submit.sh.
# The values of nequip_no_zbl.sh, so the potentials' runs differ only in the model; TMELT and HOLD_PS confirmed by
# this model's superheating pilot, x0 r1 and x10 r1 (job 12431656, 2026-11-18; RUNBOOK.md, meltquench step 1),
# which are production runs (same seeds as nequip_no_zbl's).

SIZE=444            # supercell, as nequip_no_zbl (structures/444/, 29.5k-32.8k atoms, 96.5 A box), so the glasses compare
                    #   cell for cell
NGPU=${NGPU:-2}     # GPUs (= MPI ranks) per run, as nequip_no_zbl; a submission may set another value, e.g.
                    #   --export=ALL,NGPU=3 on 3 A30s
TMELT=1500          # K. Pilot: Tm_app 1133 K (x0) and 956 K (x10) on the 10 K/ps heat, so 1500 K is 367 K above the
                    #   higher; closest approach in the 1500 K liquid C-C 1.08 A, Ge-C 1.60 A, Te-C 1.74 A (x10), Ge/Sb/Te pairs >= 2.08 A
HOLD_PS=100         # ps at TMELT. Pilot: smallest per-species MSD in the hold 654.7 A^2 (x0), 337.2 A^2 (x10), gate 100.
QRATE=10            # K/ps, as nequip_no_zbl

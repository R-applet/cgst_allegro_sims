# Melt-quench design numbers for MODEL_ID=nequip_no_zbl, each with where it came from. Sourced by meltquench/submit.sh
# and, for QRATE, SIZE and NGPU, by recryst/params/nequip_no_zbl.sh. TMELT and HOLD_PS were provisional until the
# superheating pilot, x0 r1 and x10 r1 (job 12359216, 2026-11-13; meltquench/results/nequip_no_zbl/), confirmed them;
# the pilot runs are production runs (same seeds).

SIZE=444            # supercell, structures/<SIZE>/ (4x4x4, 29.5k-32.8k atoms, 96.5 A box). Chosen 2026-11-13 for
                    #   nucleation statistics and a longer v_growth window; cost 2.37x per run vs 333
                    #   (tests/scaling/RESULT_size.txt)
NGPU=${NGPU:-2}     # GPUs (= MPI ranks) per run, enforced by the submit scripts (the job's ranks must equal NGPU); a
                    #   submission may set another value, e.g. --export=ALL,NGPU=3 on 3 A30s (24 GB each). At 444 one
                    #   A100-40GB holds the x10 cell with 6 GB to spare (34.3 of 41 GB, 600 K solid); 2 GPUs: 23.3 GB each, 2.59 ns/day = 1.93x
                    #   one GPU's 1.34 (tests/scaling/submit_size.sh, jobs 12358493-94). Decided 2026-11-13.
TMELT=1500          # K. Pilot: Tm_app 1139 K (x0) and 983 K (x10) on the 10 K/ps heat, so 1500 K is 361 K above the
                    #   higher; closest approach in the 1500 K liquid >= 2.06 A for Ge/Sb/Te pairs, C-C 1.08 A (x10),
                    #   no pair below 1.0 A despite no ZBL.
HOLD_PS=100         # ps at TMELT. Pilot: smallest per-species MSD in the hold 651 A^2 (x0), 354 A^2 (x10), gate 100.
QRATE=10            # K/ps. Confirmed for this model: 1 K/ps partially crystallizes the
                    #   glass (xfracGST 0.30 at x0 vs 0.14 at 10 K/ps), 5 K/ps barely changes it (0.16)
                    #   (results/nequip_no_zbl/RESULTS.md, Quench rate).

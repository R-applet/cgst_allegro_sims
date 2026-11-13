# Melt-quench design numbers for MODEL_ID=nozbl_paw. PROVISIONAL: copied from run5_ep301 on 2026-11-13; the
# superheating pilot (x0 r1 and x10 r1, RUNBOOK.md, meltquench step 1) confirms or replaces each value. Record the
# pilot's numbers here as the provenance when it is done.

SIZE=444            # supercell, structures/<SIZE>/ (4x4x4, 29.5k-32.8k atoms, 96.5 A box). Chosen 2026-11-13 for
                    #   nucleation statistics and a longer v_growth window; cost ~2.4x per run vs 333
                    #   (measured: tests/scaling/submit_size.sh)
NGPU=2              # GPUs (= MPI ranks) per run, enforced by the submit scripts. At 444 one A100-40GB holds the x10
                    #   cell with 6 GB to spare (34.3 of 41 GB, 600 K solid); 2 GPUs: 23.3 GB each, 2.59 ns/day = 1.93x
                    #   one GPU's 1.34 (tests/scaling/submit_size.sh, jobs 12358493-94). Decided 2026-11-13.
TMELT=1500          # K. PROVISIONAL. Needs >= ~300 K above the pilot's highest Tm_app, MSD gate passed, and no close
                    #   contacts (mq_summary.py rmin_*; this model has no ZBL repulsion).
HOLD_PS=100         # ps at TMELT. PROVISIONAL (MSD gate >= 100 A^2 in the pilot).
QRATE=10            # K/ps. Kept from run5_ep301 (1 K/ps partially crystallized its glasses).

# Melt-quench design numbers for MODEL_ID=nozbl_paw. PROVISIONAL: copied from run5_ep301 on 2026-11-13; the
# superheating pilot (x0 r1 and x10 r1, RUNBOOK.md, meltquench step 1) confirms or replaces each value. Record the
# pilot's numbers here as the provenance when it is done.

TMELT=1500          # K. PROVISIONAL. Needs >= ~300 K above the pilot's highest Tm_app, MSD gate passed, and no close
                    #   contacts (mq_summary.py rmin_*; this model has no ZBL repulsion).
HOLD_PS=100         # ps at TMELT. PROVISIONAL (MSD gate >= 100 A^2 in the pilot).
QRATE=10            # K/ps. Kept from run5_ep301 (1 K/ps partially crystallized its glasses).

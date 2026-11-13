# Melt-quench design numbers for MODEL_ID=run5_ep301, each with where it came from. Sourced by meltquench/submit.sh
# and, for QRATE and SIZE (which glasses recryst starts from, and its crystal references), by
# recryst/params/run5_ep301.sh. For a new model, copy this file
# to meltquench/params/<MODEL_ID>.sh and set every value from that model's superheating pilot (RUNBOOK.md, meltquench).

SIZE=333            # supercell, structures/<SIZE>/ (3x3x3, 12.4k-13.8k atoms, 72.4 A box)
# NGPU unset: run5_ep301 ran on 2 A30s or 1 A100 per run (3x3x3), not enforced.
TMELT=1500          # K. Superheated melting on a 10 K/ps heat: Tm_app 1129 K (x0) to 984 K (x10)
                    #   (results/run5_ep301/RESULTS.md); 1500 K gives a fast liquid (MSD gate passed in all 17 runs).
HOLD_PS=100         # ps at TMELT; every run passed the MSD gate (>= 100 A^2) with it.
QRATE=10            # K/ps. 1 K/ps partially crystallizes the glass (xfracGST 0.28 vs 0.13-0.16), so recryst uses 10.

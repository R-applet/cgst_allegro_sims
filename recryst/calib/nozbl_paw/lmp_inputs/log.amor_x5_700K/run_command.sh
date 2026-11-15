#!/bin/bash
# Recorded 2026-11-14 22:06:41 by common/record_inputs.sh; reference copy, not used to submit.
# The input as run is in.calib in this directory; the command reads the original path.
cd /scratch/gilbreth/rapplet/cgst_allegro_sims/recryst/calib/nozbl_paw
/scratch/gilbreth/rapplet/cgst_allegro_sims/common/run_lmp.sh 2 -in ../in.calib -log log.amor_x5_700K -var root /scratch/gilbreth/rapplet/cgst_allegro_sims -var src /scratch/gilbreth/rapplet/cgst_allegro_sims/meltquench/runs/nozbl_paw/x5_q10_r1/amorphous_300K.data -var T 700 -var tag amor_x5_700K -var seed 1920432 -var dt 0.002 -var minimize 0 -var model /scratch/gilbreth/rapplet/cgst_allegro_sims/models/nozbl_paw.N.nequip.pt2 

#!/bin/bash
# Recorded 2026-11-14 20:42:02 by common/record_inputs.sh; reference copy, not used to submit.
# The input as run is in.calib in this directory; the command reads the original path.
cd /scratch/gilbreth/rapplet/cgst_allegro_sims/recryst/calib/nozbl_paw
/scratch/gilbreth/rapplet/cgst_allegro_sims/common/run_lmp.sh 2 -in ../in.calib -log log.crys_x1_300K -var root /scratch/gilbreth/rapplet/cgst_allegro_sims -var src /scratch/gilbreth/rapplet/cgst_allegro_sims/structures/444/x1.data -var T 300 -var tag crys_x1_300K -var seed 280063 -var dt 0.002 -var minimize 1 -var model /scratch/gilbreth/rapplet/cgst_allegro_sims/models/nozbl_paw.N.nequip.pt2 

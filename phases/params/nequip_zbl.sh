# Phases design numbers for MODEL_ID=nequip_zbl. Sourced by phases/submit.sh (NVT) and submit_npt.sh (NPT) after
# common/defaults.sh. Every value is set by the DFT reference, not by the model, so a new potential copies this file
# unchanged (phases/README.md).
PHASES=(am_gst am_c1 am_c5 am_c10 cub_gst cub_c1 hex_gst hex_c1)   # phases/structures/<phase>.data; the 8 cells with
                    #   DFT RDF/ADF/VDOS (phases/dft/). Array index i -> PHASES[i / NREP], replica i % NREP + 1.
NREP=3              # seeds per phase (decided 2026-11-16): the Allegro spread against one DFT trajectory per phase.
TEMP=300            # K, the DFT-MD temperature.
DT=0.001            # ps. 1 fs as in the DFT-MD, so DoSPT sees the same sampling (dospt_input.txt: 20000 points in
                    #   20 ps); this overrides the model's production DT (2 fs, tests/dt) for this study only.
EQ_PS=5             # ps discarded (DFT: the first 5000 frames of 25000, dospt_example/sample.py).
PROD_PS=20          # ps analysed, every step.
TDAMP_PS=0.1        # ps, Nose-Hoover damping (100 steps, as in the preliminary Allegro input).

# NPT at 0 bar (in.npt, submit_npt.sh): the potential's own density and cell of each phase, NREP seeds, TEMP and DT
# and TDAMP_PS as above. Seeds are those of the NVT runs of the same phase (submit_npt.sh).
NPT_PHASES=(am_gst cub_gst hex_gst)   # the C-free cells: amorphous (iso barostat), rocksalt and trigonal (tri)
NPT_PS=500          # ps; the volume settles within 50-100 ps in every run (2026-11-17/18)
NPT_AVG_PS=100      # ps discarded before averaging the density (analysis/phases_npt.py)
PDAMP_PS=1.0        # ps, Nose-Hoover barostat damping (1000 steps)

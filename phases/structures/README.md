# Phase cells (DFT-sized)

The 8 cells of the 300 K DFT-MD that `phases/dft/` holds RDF/ADF/VDOS for, as 4-type LAMMPS data files written by
`convert_dft_cells.py` from `$DFT_PHASES/<amorph|cubic|hex>/<gst|c1|c5|c10>/lammps/*.data` (`common/model.sh`).
Box, tilts and atom order are the DFT ones (the DFT per-atom DOS is indexed by atom order); atoms are wrapped into
the box and a Masses section is added. Types: 1 Ge, 2 Sb, 3 Te, 4 C.

| phase | atoms | Ge/Sb/Te/C | cell | V (Å³/atom) |
|---|---|---|---|---|
| am_gst | 144 | 32/32/80/0 | cubic | 30.59 |
| am_c1 | 146 | 32/32/80/2 | cubic | 30.25 |
| am_c5 | 152 | 32/32/80/8 | cubic | 28.86 |
| am_c10 | 160 | 32/32/80/16 | cubic | 27.70 |
| cub_gst | 144 | 32/32/80/0 | triclinic (rocksalt) | 30.02 |
| cub_c1 | 146 | 32/32/80/2 | triclinic (rocksalt) | 29.65 |
| hex_gst | 144 | 32/32/80/0 | hexagonal (trigonal GST) | 29.55 |
| hex_c1 | 146 | 32/32/80/2 | hexagonal (trigonal GST) | 29.20 |

C contents are 0, 1.4, 5.3 and 10.0 at.%, not the 0–9.96 at.% of `structures/` (x0–x10): these are separate cells.

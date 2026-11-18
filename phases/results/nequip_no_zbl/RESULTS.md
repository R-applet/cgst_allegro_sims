# Phases results: nequip_no_zbl

Method: `phases/README.md`. Settings: `phases/params/nequip_no_zbl.sh` (8 DFT cells of 144–160 atoms, 300 K Nosé–Hoover
NVT at the DFT volume, 1 fs, 5 ps equilibration + 20 ps production dumped every step, 3 seeds per phase). Runs in
`phases/runs/nequip_no_zbl/nvt/`, each with its input record in `lmp_inputs/log.phases/`. Analysis:
`analysis/phases_compare.py` (definitions in its docstring), through `phases/submit_analysis.sh`.

**Status (2026-11-16):** done. 24 standard runs (pilot array 12402180 tasks 9 and 21, production array 12402403) and
12 longer-equilibration runs of the amorphous cells (`_eq25`, array 12402404), 1.3–2.2 min each on one A30. Analysis
jobs 12402649 and 12402793 analysed every run; their `compare` stage failed on two bugs fixed afterwards (the hex_c1
DFT ADF has 100 bins, not 90; a variable name clash), and `compare` was rerun on its own. Outputs here:
`phases_summary.txt` (per phase, mean ± sample std over the 3 seeds), `phases_runs.txt` (per run),
`phases_relaxation.txt`, `figures/summary.png|pdf` (the metrics below across the phases, every seed shown),
`figures/<group>.png|pdf` (RDF, ADF, VDOS by species, VDOS of C) and `figures/relaxation_pe.png|pdf`.

## Checks
- **Runs:** no errors; production-window mean T 297.5–302.0 K in every run; the Nosé–Hoover conserved energy drifts
  by at most 6e-6 eV/atom over the 20 ps window (`thermo.dat`).
- **DoSPT velocities:** the VDOS from DoSPT's finite-difference velocities equals the one from the dumped exact
  velocities (overlap 1.0000; am_c10 r1 and hex_c1 r1, `vdos_species_v.txt`). Dumped positions carry 8 decimals.
- **RDF/ADF definitions:** run on the hex_gst DFT trajectory itself (`dft-check`, every 10th of 20000 frames), this
  code reproduces the DFT files: ADF overlap 0.9997, angles per frame equal (ratio 1.0000), RDF R 0.015.
- **DoSPT build:** `analysis/build_dospt.sh check` reproduces the depot's `dospt_example` DOS (max difference 1.6e-20).
  In every run DoSPT read the cell of the box (its printed cell diagonal equals the box's, checked by `analyze`).
- **DFT species DOS:** `phases/dft/<phase>/vdos_species.txt` sums the per-atom blocks by the atom types of the data
  files; the sum of species equals the file's total block (≤ 1.4e-15). Compared with the preliminary `plot_dos.py`
  sums, Ge agrees (1e-6, rounding), but `plot_dos.py` takes the Sb and Te blocks one atom early (Sb = atoms 32–63,
  Te = 64–143 instead of 33–64 and 65–144), off by 5–8% in Sb and 1–4% in Te; shifted by one atom they agree to
  1e-6. The preliminary per-species DFT plots carry that error; the references here do not.

## Allegro vs DFT (mean of 3 seeds; DFT in brackets)

| phase | RDF R | first peak r (Å) | first peak g | ADF overlap | VDOS overlap | ⟨ν⟩ (THz) |
|---|---|---|---|---|---|---|
| am_gst | 0.053 ± 0.007 | 2.88 (2.88) | 2.21 (2.29) | 0.922 ± 0.006 | 0.945 ± 0.010 | 2.63 (2.74) |
| am_c1 | 0.076 ± 0.008 | 2.88 (2.88) | 2.16 (2.09) | 0.945 ± 0.012 | 0.938 ± 0.004 | 2.71 (2.88) |
| am_c5 | 0.054 ± 0.005 | 2.91 (2.88) | 1.74 (1.80) | 0.966 ± 0.003 | 0.928 ± 0.000 | 3.21 (3.27) |
| am_c10 | 0.071 ± 0.013 | 2.93 (2.88) | 1.81 (1.79) | 0.954 ± 0.004 | 0.918 ± 0.006 | 3.85 (3.85) |
| cub_gst | 0.049 ± 0.002 | 2.99 (3.00) | 3.51 (3.32) | 0.971 ± 0.002 | 0.902 ± 0.007 | 2.75 (2.78) |
| cub_c1 | 0.074 ± 0.006 | 2.99 (2.98) | 3.37 (3.02) | 0.963 ± 0.002 | 0.913 ± 0.004 | 2.87 (2.90) |
| hex_gst | 0.064 ± 0.001 | 2.99 (2.96) | 3.82 (3.66) | 0.964 ± 0.004 | 0.869 ± 0.006 | 2.80 (2.82) |
| hex_c1 | 0.053 ± 0.003 | 2.98 (2.96) | 3.52 (3.42) | 0.983 ± 0.003 | 0.903 ± 0.001 | 3.18 (3.00) |

R is the RDF misfit over 1.5–6 Å relative to the DFT g(r) (0 = identical); the overlaps are the shared area of the two
normalized curves (1 = identical); ⟨ν⟩ is the mean frequency of the total VDOS.

Mean frequency per species (THz):

| phase | Ge | Sb | Te | C | C VDOS overlap |
|---|---|---|---|---|---|
| am_gst | 3.44 (3.52) | 2.48 (2.59) | 2.37 (2.49) | — | — |
| am_c1 | 3.43 (3.72) | 2.47 (2.63) | 2.37 (2.51) | 14.1 ± 1.1 (14.7) | 0.63 |
| am_c5 | 3.80 (4.07) | 2.55 (2.76) | 2.40 (2.56) | 15.1 ± 0.3 (14.2) | 0.70 |
| am_c10 | 3.96 (4.14) | 2.53 (2.80) | 2.39 (2.58) | 17.5 ± 0.5 (15.1) | 0.72 |
| cub_gst | 3.01 (3.10) | 2.69 (2.75) | 2.67 (2.66) | — | — |
| cub_c1 | 2.98 (3.14) | 2.64 (2.74) | 2.65 (2.69) | 11.0 ± 1.1 (11.0) | 0.66 |
| hex_gst | 2.89 (2.93) | 2.76 (2.80) | 2.77 (2.78) | — | — |
| hex_c1 | 2.99 (3.07) | 2.76 (2.80) | 2.74 (2.78) | 13.7 ± 0.3 (12.7) | 0.61 |

- **Structure agrees closely.** RDF R is 0.05–0.08 and the first peak sits within 0.05 Å of DFT's everywhere. In
  the crystals Allegro's first peak is 3–12% taller (cub_c1 3.37 against 3.02): slightly less thermal disorder at
  300 K. ADF overlap is 0.92–0.98, with the bond-angle peak at 89–91° as in DFT.
- **Ge/Sb/Te vibrations are a little soft in the amorphous cells.** Their mean frequencies are 2–9% below DFT's,
  most for Sb in am_c10 (2.53 against 2.80 THz) and Ge in am_c1 (−8%). In the crystals they are within 0–5%.
- **Trigonal GST has the wrong shape in its main band.** RDF and ADF match, and the mean frequencies agree within
  1.5%, but Allegro puts a sharp Ge/Te peak near 2.9 THz where DFT has a broad 2.6–3.4 THz band (`figures/hex_gst.png`).
  This gives the lowest VDOS overlap, 0.87.
- **C vibrations agree least (overlap 0.61–0.72).** The bands of C modes (6–20 THz and 30–45 THz) are in the right
  places, but individual peaks are shifted, and in am_c10 the C mean frequency is 16% above DFT's. With 2–16 C atoms
  per cell the C spectra are noisy on both sides: seeds differ by up to ±1 THz in ⟨ν_C⟩. The total ⟨ν⟩ of the
  C-containing cells follows ⟨ν_C⟩ (hex_c1 3.18 against 3.00).

## Effect of the relaxation (`phases_relaxation.txt`, `figures/relaxation_pe.png`)
The amorphous cells start from the DFT structure (`phases/structures/`), and their potential energy keeps falling after the 5 ps
equilibration: −0.010 to −0.014 eV/atom across the 20 ps window (`dPE_prod`, the mean of the last 2 ps minus the first
2 ps). The crystals drift by less than 0.002. To measure what that does to the comparison, the `_eq25` runs repeat the
amorphous cells with the same seeds and a 25 ps equilibration, so the 20 ps window starts 20 ps later on the same
trajectory. Their drift is −0.0003 to −0.004 eV/atom.

Paired by seed, the later window changes (mean differences; the spread between seeds of the standard runs in brackets):

| phase | RDF R | ADF overlap | VDOS overlap | ⟨ν⟩ Ge / Sb / Te (THz) | C VDOS overlap |
|---|---|---|---|---|---|
| am_gst | +0.002 [0.007] | +0.001 [0.006] | +0.002 [0.010] | +0.00 / −0.02 / +0.02 | — |
| am_c1 | +0.007 [0.008] | −0.012 [0.012] | +0.000 [0.004] | +0.08 / +0.03 / +0.04 | −0.036 [0.026] |
| am_c5 | +0.014 [0.005] | −0.012 [0.003] | +0.007 [0.000] | +0.07 / +0.03 / +0.04 | −0.036 [0.044] |
| am_c10 | +0.002 [0.013] | −0.007 [0.004] | −0.007 [0.006] | +0.02 / +0.05 / −0.00 | −0.035 [0.018] |

The relaxation stiffens the Ge/Sb/Te vibrations by up to 0.08 THz (≤ 2%, toward DFT) and moves every structural and
spectral metric by about the seed-to-seed spread or less; am_c5's RDF R and ADF overlap move by 2–4 spreads, still by
only 0.014 and 0.012. **No conclusion above changes.** The standard window, which is the one DFT used (the first 5 of
25 ps discarded), stays the main comparison.

## Density at 0 bar (NPT; `npt_runs.txt`, `npt_summary.txt`)

The C-free cells at 300 K and 0 bar for 500 ps, 3 seeds each (those of the NVT runs; `phases/in.npt`, isotropic
barostat for the amorphous cell, full cell relaxation for the crystals), jobs 12414363 (amorphous, 2026-11-17) and 12429530 (crystals, 2026-11-18) on alta k-nodes; density averaged
over 100–500 ps, ± the standard error over the seeds. Runs in `phases/runs/nequip_no_zbl/npt/`. They were run before
`phases/in.npt` and `submit_npt.sh` existed, with inputs outside the repository (recorded in
each run's `lmp_inputs/`) that have the same settings as `in.npt`.

| phase | DFT cell (g/cc) | nequip_no_zbl (g/cc) | nequip_zbl / rushik_zbl_pairwise | PE (eV/atom) |
|---|---|---|---|---|
| am_gst | 6.193 | 6.251 ± 0.013 | 6.246 / 6.232 | -0.112 |
| cub_gst | 6.311 | 6.241 ± 0.000 | 6.248 / 6.245 | -0.219 |
| hex_gst | 6.412 | 6.343 ± 0.000 | 6.342 / 6.321 | -0.256 |

- **Cubic crystal vs glass -0.15% ± 0.21%, hexagonal +1.47% ± 0.21%** (in density; the
  crystals are 107 and 144 meV/atom lower in energy). The three potentials agree
  (`../npt_compare.txt`): the rocksalt crystal is as dense as the glass, the trigonal one about 1.5% denser.
- The DFT cells are not at this potential's zero pressure: the crystals expand by about 1% and the glass contracts,
  so the DFT-cell gaps (cubic +1.9%, hexagonal +3.5%) mostly close at 0 bar.
- Each crystal stays crystalline (no drift of density or PE over 500 ps); the cells stretch about 0.85% along one
  axis (cubic) and 0.8–0.9% along c (hexagonal). The glass seeds settle 0.02–0.03 g/cc apart and stay there.

## Caveats
- **The DFT ADF files used two Sb–Te bond cutoffs.** The depot's `compute_adf.py` scripts say 3.4 Å, but hex_gst's
  file was made with 3.2 Å (shown on its trajectory, Checks). Each Allegro ADF is computed with both, and `compare`
  uses for each phase the one whose angles per frame are closest to the DFT file's (`adf_sbte` in
  `phases_summary.txt`): 3.4 Å for the amorphous cells and hex_c1, 3.2 Å for cub_gst, cub_c1 and hex_gst. With that
  choice the angle counts agree within 0–7%, except **am_gst, where Allegro has 19% fewer angles than the DFT file with
  either cutoff** (`adf_count_ratio` 0.81). Its ADF shape still agrees (overlap 0.92); the DFT file may come from
  other frames or settings. Only hex_gst's DFT trajectory was available to check directly.
- **The DFT-MD of these phases is in the training data** (the AM/CUB/HEX_GST and C1/C5/C10 runs of
  `cgst_train_paw.xyz`), so this tests how well the potential reproduces its own training phases, not a prediction.
- **RDF range.** The amorphous DFT RDF files run to 10 Å, past half the 16.4 Å box (8.2 Å), where a minimum-image
  RDF is no longer complete, so every RDF metric stops at 6 Å (Allegro's RDF counts all periodic images and is exact
  to 10 Å).
- **One DFT trajectory per phase**, 144–160 atoms and 20 ps. Its statistical noise is not known; the ± here are the
  Allegro seeds' only. The C spectra (2–16 atoms) are the most affected.

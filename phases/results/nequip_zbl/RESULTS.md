# Phases results: nequip_zbl

Method: `phases/README.md`. Settings: `phases/params/nequip_zbl.sh`, identical to nequip_no_zbl's (8 DFT cells of 144–160
atoms, 300 K Nosé–Hoover NVT at the DFT volume, 1 fs, 5 ps equilibration + 20 ps production dumped every step, 3 seeds
per phase, the same seeds). Runs in `phases/runs/nequip_zbl/nvt/`. Analysis: `analysis/phases_compare.py` through
`phases/submit_analysis.sh`.

**Status (2026-11-18):** done, on perc A100-40GB n-nodes with `--export=ALL,MODEL_ID=nequip_zbl,PMIX_MCA_gds=hash`: pilot
array 12430628 (tasks 9, 21), production array 12431372, the 12 longer-equilibration runs `_eq25` (array 12431373), about 1 min
each; analysis job 12431379 (23 min). Outputs here: `phases_summary.txt`, `phases_runs.txt`, `phases_relaxation.txt`,
`figures/`.

## Checks
- Every run finished with no errors; the pilots' production-window T is within 1 K of 300 K and the conserved energy
  drifts by at most 1.2e-5 eV/atom.
- DoSPT's finite-difference VDOS equals the exact-velocity one (overlap 1.0000; am_c10 r1, hex_c1 r1); DoSPT's cell
  equals the box in all 36 runs; `dft-check` reproduces the hex_gst DFT files (ADF overlap 0.9997, angles per frame
  ratio 1.0000, RDF R 0.015).

## Allegro vs DFT (mean ± sample std of 3 seeds; nequip_no_zbl / rushik_zbl_pairwise in parentheses; DFT ⟨ν⟩ in brackets)

| phase | RDF R | ADF overlap | VDOS overlap | ⟨ν⟩ (THz) |
|---|---|---|---|---|
| am_gst | 0.046 ± 0.010 (0.053 / 0.057) | 0.927 ± 0.009 (0.922 / 0.931) | 0.953 ± 0.004 (0.945 / 0.941) | 2.62 [2.738] |
| am_c1 | 0.069 ± 0.007 (0.075 / 0.065) | 0.951 ± 0.014 (0.945 / 0.951) | 0.934 ± 0.008 (0.938 / 0.941) | 2.72 [2.875] |
| am_c5 | 0.061 ± 0.004 (0.054 / 0.061) | 0.960 ± 0.005 (0.966 / 0.969) | 0.932 ± 0.009 (0.928 / 0.925) | 3.25 [3.265] |
| am_c10 | 0.075 ± 0.009 (0.071 / 0.089) | 0.960 ± 0.006 (0.954 / 0.958) | 0.921 ± 0.012 (0.918 / 0.916) | 4.02 [3.852] |
| cub_gst | 0.047 ± 0.000 (0.049 / 0.046) | 0.972 ± 0.002 (0.971 / 0.972) | 0.909 ± 0.007 (0.902 / 0.905) | 2.73 [2.777] |
| cub_c1 | 0.071 ± 0.008 (0.074 / 0.071) | 0.967 ± 0.004 (0.963 / 0.965) | 0.914 ± 0.006 (0.913 / 0.902) | 2.98 [2.9] |
| hex_gst | 0.064 ± 0.001 (0.064 / 0.062) | 0.967 ± 0.002 (0.964 / 0.971) | 0.877 ± 0.004 (0.869 / 0.875) | 2.78 [2.817] |
| hex_c1 | 0.050 ± 0.006 (0.053 / 0.054) | 0.984 ± 0.002 (0.983 / 0.983) | 0.898 ± 0.012 (0.903 / 0.899) | 3.08 [2.999] |

Definitions as in `../nequip_no_zbl/RESULTS.md` (R: RDF misfit over 1.5–6 Å, 0 = identical; overlaps: shared area of
the normalized curves, 1 = identical). Per species and for C: `phases_summary.txt`.

**Reading: nequip_zbl reproduces the DFT phases as the other two potentials do;** every metric lies within about the seed
spread of theirs, so at 300 K the short-range term makes no measurable difference in these cells. 
The C vibrations agree least with DFT for all three potentials (C VDOS overlap 0.5–0.7, ⟨ν_C⟩ up to 20% high in
am_c10), and cub_c1's two C atoms make its C metrics noisy.

## Effect of the relaxation (`phases_relaxation.txt`)
dPE_prod (eV/atom, last minus first 2 ps of the window), standard / `_eq25`: am_gst -0.0088 / -0.0072; am_c1 -0.0147 / -0.0044; am_c5 -0.0075 / -0.0052; am_c10 -0.0095 / -0.0047. The longer
equilibration moves the Ge/Sb/Te metrics by about the seed spread or less, as for nequip_no_zbl.

## Density at 0 bar (NPT; `npt_runs.txt`, `npt_summary.txt`)

The C-free cells at 300 K and 0 bar for 500 ps, 3 seeds each (those of the NVT runs; `phases/in.npt`, isotropic
barostat for the amorphous cell, full cell relaxation for the crystals), job array 12430604 (2026-11-18) on perc n-nodes; density averaged
over 100–500 ps, ± the standard error over the seeds. Runs in `phases/runs/nequip_zbl/npt/`. They were run before
`phases/in.npt` and `submit_npt.sh` existed, with inputs outside the repository (recorded in
each run's `lmp_inputs/`) that have the same settings as `in.npt`.

| phase | DFT cell (g/cc) | nequip_zbl (g/cc) | nequip_no_zbl / rushik_zbl_pairwise | PE (eV/atom) |
|---|---|---|---|---|
| am_gst | 6.193 | 6.246 ± 0.016 | 6.251 / 6.232 | -0.109 |
| cub_gst | 6.311 | 6.248 ± 0.000 | 6.241 / 6.245 | -0.220 |
| hex_gst | 6.412 | 6.342 ± 0.000 | 6.343 / 6.321 | -0.255 |

- **Cubic crystal vs glass +0.03% ± 0.25%, hexagonal +1.55% ± 0.25%** (in density; the
  crystals are 111 and 146 meV/atom lower in energy). The three potentials agree
  (`../../report/npt_compare.txt`): the rocksalt crystal is as dense as the glass, the trigonal one about 1.5% denser.
- The DFT cells are not at this potential's zero pressure: the crystals expand by about 1% and the glass contracts,
  so the DFT-cell gaps (cubic +1.9%, hexagonal +3.5%) mostly close at 0 bar.
- Each crystal stays crystalline (no drift of density or PE over 500 ps); the cells stretch about 0.85% along one
  axis (cubic) and 0.8–0.9% along c (hexagonal). The glass seeds settle 0.02–0.03 g/cc apart and stay there.

The three potentials compared, with figures and slides: `phases/report/` (`phases_report.pdf`).

## Caveats
Those of `../nequip_no_zbl/RESULTS.md` apply unchanged (the DFT references and the method): the DFT-MD of these
phases is training data, the 6 Å RDF range, one DFT trajectory per phase, and the two Sb–Te ADF cutoffs.

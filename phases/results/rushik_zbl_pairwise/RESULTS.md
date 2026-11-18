# Phases results: rushik_zbl_pairwise

Method: `phases/README.md`. Settings: `phases/params/rushik_zbl_pairwise.sh`, identical to nequip_no_zbl's (8 DFT cells of 144–160
atoms, 300 K Nosé–Hoover NVT at the DFT volume, 1 fs, 5 ps equilibration + 20 ps production dumped every step, 3 seeds
per phase, the same seeds). Runs in `phases/runs/rushik_zbl_pairwise/nvt/`. Analysis: `analysis/phases_compare.py` through
`phases/submit_analysis.sh`.

**Status (2026-11-18):** done, on perc A100-40GB n-nodes with `--export=ALL,MODEL_ID=rushik_zbl_pairwise,PMIX_MCA_gds=hash`: pilot
array 12430629 (tasks 9, 21), production array 12431374, the 12 longer-equilibration runs `_eq25` (array 12431375), about 1 min
each; analysis job 12431380 (23 min). Outputs here: `phases_summary.txt`, `phases_runs.txt`, `phases_relaxation.txt`,
`figures/`.

## Checks
- Every run finished with no errors; the pilots' production-window T is within 1 K of 300 K and the conserved energy
  drifts by at most 1.2e-5 eV/atom.
- DoSPT's finite-difference VDOS equals the exact-velocity one (overlap 1.0000; am_c10 r1, hex_c1 r1); DoSPT's cell
  equals the box in all 36 runs; `dft-check` reproduces the hex_gst DFT files (ADF overlap 0.9997, angles per frame
  ratio 1.0000, RDF R 0.015).

## Allegro vs DFT (mean ± sample std of 3 seeds; nequip_no_zbl / nequip_zbl in parentheses; DFT ⟨ν⟩ in brackets)

| phase | RDF R | ADF overlap | VDOS overlap | ⟨ν⟩ (THz) |
|---|---|---|---|---|
| am_gst | 0.057 ± 0.013 (0.053 / 0.046) | 0.931 ± 0.004 (0.922 / 0.927) | 0.941 ± 0.005 (0.945 / 0.953) | 2.62 [2.738] |
| am_c1 | 0.065 ± 0.010 (0.075 / 0.069) | 0.951 ± 0.004 (0.945 / 0.951) | 0.941 ± 0.004 (0.938 / 0.934) | 2.75 [2.875] |
| am_c5 | 0.061 ± 0.009 (0.054 / 0.061) | 0.969 ± 0.008 (0.966 / 0.960) | 0.925 ± 0.008 (0.928 / 0.932) | 3.29 [3.265] |
| am_c10 | 0.089 ± 0.011 (0.071 / 0.075) | 0.958 ± 0.002 (0.954 / 0.960) | 0.916 ± 0.003 (0.918 / 0.921) | 3.99 [3.852] |
| cub_gst | 0.046 ± 0.000 (0.049 / 0.047) | 0.972 ± 0.001 (0.971 / 0.972) | 0.905 ± 0.008 (0.902 / 0.909) | 2.76 [2.777] |
| cub_c1 | 0.071 ± 0.003 (0.074 / 0.071) | 0.965 ± 0.005 (0.963 / 0.967) | 0.902 ± 0.010 (0.913 / 0.914) | 2.88 [2.9] |
| hex_gst | 0.062 ± 0.002 (0.064 / 0.064) | 0.971 ± 0.005 (0.964 / 0.967) | 0.875 ± 0.003 (0.869 / 0.877) | 2.77 [2.817] |
| hex_c1 | 0.054 ± 0.003 (0.053 / 0.050) | 0.983 ± 0.000 (0.983 / 0.984) | 0.899 ± 0.005 (0.903 / 0.898) | 3.19 [2.999] |

Definitions as in `../nequip_no_zbl/RESULTS.md` (R: RDF misfit over 1.5–6 Å, 0 = identical; overlaps: shared area of
the normalized curves, 1 = identical). Per species and for C: `phases_summary.txt`.

**Reading: rushik_zbl_pairwise reproduces the DFT phases as the other two potentials do;** every metric but one lies within about
the seed spread of theirs, so at 300 K the short-range term makes no measurable difference in these cells. The one
difference larger than the seed spread is the RDF misfit of amorphous GST + 10% C (R 0.089 ± 0.011 against 0.071 and
0.075): the C-bond peak at 2.0 Å is taller than DFT's (g ≈ 0.9 against 0.65) and the second shell (3.4–4.8 Å) sits
slightly outward, below DFT's on its inner side and above it on its outer side (`figures/am_c10.png`).
The C vibrations agree least with DFT for all three potentials (C VDOS overlap 0.5–0.7, ⟨ν_C⟩ up to 20% high in
am_c10), and cub_c1's two C atoms make its C metrics noisy.

## Effect of the relaxation (`phases_relaxation.txt`)
dPE_prod (eV/atom, last minus first 2 ps of the window), standard / `_eq25`: am_gst -0.0074 / -0.0049; am_c1 -0.0107 / -0.0055; am_c5 -0.0109 / -0.0017; am_c10 -0.0123 / -0.0046. The longer
equilibration moves the Ge/Sb/Te metrics by about the seed spread or less, as for nequip_no_zbl.

## Density at 0 bar (NPT; `npt_runs.txt`, `npt_summary.txt`)

The C-free cells at 300 K and 0 bar for 500 ps, 3 seeds each (those of the NVT runs; `phases/in.npt`, isotropic
barostat for the amorphous cell, full cell relaxation for the crystals), job array 12430604 (2026-11-18) on perc n-nodes; density averaged
over 100–500 ps, ± the standard error over the seeds. Runs in `phases/runs/rushik_zbl_pairwise/npt/`. They were run before
`phases/in.npt` and `submit_npt.sh` existed, with inputs outside the repository (recorded in
each run's `lmp_inputs/`) that have the same settings as `in.npt`.

| phase | DFT cell (g/cc) | rushik_zbl_pairwise (g/cc) | nequip_no_zbl / nequip_zbl | PE (eV/atom) |
|---|---|---|---|---|
| am_gst | 6.193 | 6.232 ± 0.011 | 6.251 / 6.246 | -0.110 |
| cub_gst | 6.311 | 6.245 ± 0.000 | 6.241 / 6.248 | -0.219 |
| hex_gst | 6.412 | 6.321 ± 0.000 | 6.343 / 6.342 | -0.254 |

- **Cubic crystal vs glass +0.20% ± 0.18%, hexagonal +1.41% ± 0.18%** (in density; the
  crystals are 109 and 144 meV/atom lower in energy). The three potentials agree
  (`../npt_compare.txt`): the rocksalt crystal is as dense as the glass, the trigonal one about 1.5% denser.
- The DFT cells are not at this potential's zero pressure: the crystals expand by about 1% and the glass contracts,
  so the DFT-cell gaps (cubic +1.9%, hexagonal +3.5%) mostly close at 0 bar.
- Each crystal stays crystalline (no drift of density or PE over 500 ps); the cells stretch about 0.85% along one
  axis (cubic) and 0.8–0.9% along c (hexagonal). The glass seeds settle 0.02–0.03 g/cc apart and stay there.

## Caveats
Those of `../nequip_no_zbl/RESULTS.md` apply unchanged (the DFT references and the method): the DFT-MD of these
phases is training data, the 6 Å RDF range, one DFT trajectory per phase, and the two Sb–Te ADF cutoffs.

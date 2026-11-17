# Phases results: zbl_paw

Method: `phases/README.md`. Settings: `phases/params/zbl_paw.sh`, identical to nozbl_paw's (8 DFT cells of 144–160
atoms, 300 K Nosé–Hoover NVT at the DFT volume, 1 fs, 5 ps equilibration + 20 ps production dumped every step, 3 seeds
per phase, the same velocity seeds). Runs in `phases/runs/zbl_paw/`, each with its input record in
`lmp_inputs/log.phases/`. Analysis: `analysis/phases_compare.py` through `phases/submit_analysis.sh`. nozbl_paw's
results, the reference for every comparison below: `../nozbl_paw/RESULTS.md`.

**Status (2026-11-17):** done. Run on perc A100-40GB (the A30 queue was days long): pilot array 12404817 (tasks 9 and
21), production array 12404848 and the 12 longer-equilibration runs `_eq25` (array 12404849), 1.0–1.7 min each.
Every job was submitted with `--export=ALL,PMIX_MCA_gds=hash` (`RUNBOOK.md`, PMIx). Analysis job 12410167 (23 min)
analysed all 36 runs and ran `dft-check` and `compare` in one pass. Outputs here: `phases_summary.txt`,
`phases_runs.txt`, `phases_relaxation.txt`, `figures/summary.png|pdf`, `figures/<group>.png|pdf`,
`figures/relaxation_pe.png|pdf`.

**Verdict: zbl_paw reproduces the DFT phases as well as nozbl_paw, metric for metric, with one exception:** the
second shell of amorphous GST + 10% C (RDF R 0.091 against nozbl_paw's 0.071). At 300 K the two potentials (with and
without the per-pair ZBL term, trained separately on the same data) share the same strengths and the same weaknesses (soft Ge/Sb/Te in the glasses, the sharp 2.9 THz peak of trigonal GST, C spectra overlap 0.5–0.7).

## Checks
- **Runs:** no errors or lost atoms; production-window mean T 297.9–301.9 K in every run; the Nosé–Hoover conserved
  energy drifts by at most 7e-6 eV/atom over the 20 ps window (`thermo.dat`).
- **DoSPT velocities:** the VDOS from DoSPT's finite-difference velocities equals the one from the dumped exact
  velocities (overlap 1.0000; am_c10 r1 and hex_c1 r1).
- **DoSPT cell:** in all 36 runs DoSPT's printed cell diagonal equals the box (checked by `analyze`).
- **RDF/ADF definitions:** `dft-check` on the hex_gst DFT trajectory reproduces the DFT files (ADF overlap 0.9997,
  angles per frame ratio 1.0000, RDF R 0.015), as for nozbl_paw. The DFT references (`phases/dft/`) are shared.

## Allegro vs DFT (mean ± sample std of 3 seeds; nozbl_paw in parentheses, DFT in brackets)

| phase | RDF R | first peak r (Å) | first peak g | ADF overlap | VDOS overlap | ⟨ν⟩ (THz) |
|---|---|---|---|---|---|---|
| am_gst | 0.054 ± 0.002 (0.053) | 2.88 [2.88] | 2.21 [2.29] | 0.926 ± 0.009 (0.922) | 0.945 ± 0.002 (0.945) | 2.65 (2.63) [2.74] |
| am_c1 | 0.067 ± 0.014 (0.076) | 2.88 [2.88] | 2.19 [2.09] | 0.947 ± 0.013 (0.945) | 0.940 ± 0.001 (0.938) | 2.73 (2.71) [2.88] |
| am_c5 | 0.062 ± 0.012 (0.054) | 2.89 [2.88] | 1.80 [1.80] | 0.961 ± 0.008 (0.966) | 0.927 ± 0.010 (0.928) | 3.23 (3.21) [3.27] |
| am_c10 | **0.091 ± 0.006 (0.071)** | 2.93 [2.88] | 1.85 [1.79] | 0.957 ± 0.009 (0.954) | 0.915 ± 0.006 (0.918) | 3.94 (3.85) [3.85] |
| cub_gst | 0.050 ± 0.002 (0.049) | 2.99 [3.00] | 3.53 [3.32] | 0.969 ± 0.002 (0.971) | 0.903 ± 0.009 (0.902) | 2.76 (2.75) [2.78] |
| cub_c1 | 0.071 ± 0.005 (0.074) | 3.00 [2.98] | 3.34 [3.02] | 0.964 ± 0.002 (0.963) | 0.912 ± 0.007 (0.913) | 2.92 (2.87) [2.90] |
| hex_gst | 0.063 ± 0.002 (0.064) | 2.99 [2.96] | 3.84 [3.66] | 0.967 ± 0.003 (0.964) | 0.873 ± 0.012 (0.869) | 2.78 (2.80) [2.82] |
| hex_c1 | 0.052 ± 0.002 (0.053) | 2.98 [2.96] | 3.52 [3.42] | 0.983 ± 0.001 (0.983) | 0.905 ± 0.005 (0.903) | 3.09 (3.18) [3.00] |

R is the RDF misfit over 1.5–6 Å relative to the DFT g(r) (0 = identical); the overlaps are the shared area of the two
normalized curves (1 = identical); ⟨ν⟩ is the mean frequency of the total VDOS.

Mean frequency per species (THz) and the C VDOS overlap:

| phase | Ge | Sb | Te | C | C VDOS overlap |
|---|---|---|---|---|---|
| am_gst | 3.50 (3.44) [3.52] | 2.48 (2.48) [2.59] | 2.38 (2.37) [2.49] | — | — |
| am_c1 | 3.48 (3.43) [3.72] | 2.47 (2.47) [2.63] | 2.37 (2.37) [2.51] | 14.4 ± 0.4 (14.1) [14.7] | 0.64 ± 0.06 (0.63) |
| am_c5 | 3.79 (3.80) [4.07] | 2.54 (2.55) [2.76] | 2.40 (2.40) [2.56] | 15.4 ± 1.0 (15.1) [14.2] | 0.68 ± 0.02 (0.70) |
| am_c10 | 3.86 (3.96) [4.14] | 2.50 (2.53) [2.80] | 2.37 (2.39) [2.58] | 17.3 ± 0.1 (17.5) [15.1] | 0.72 ± 0.01 (0.72) |
| cub_gst | 3.02 (3.01) [3.10] | 2.69 (2.69) [2.75] | 2.68 (2.67) [2.66] | — | — |
| cub_c1 | 3.02 (2.98) [3.14] | 2.62 (2.64) [2.74] | 2.65 (2.65) [2.69] | 12.7 ± 1.8 (11.0) [11.0] | 0.49 ± 0.19 (0.66) |
| hex_gst | 2.87 (2.89) [2.93] | 2.74 (2.76) [2.80] | 2.75 (2.77) [2.78] | — | — |
| hex_c1 | 2.96 (2.99) [3.07] | 2.77 (2.76) [2.80] | 2.73 (2.74) [2.78] | 13.9 ± 0.3 (13.7) [12.7] | 0.56 ± 0.08 (0.61) |

- **The two potentials agree with each other more closely than either agrees with DFT.** Total VDOS overlaps are
  within 0.004 of nozbl_paw's in every phase, ADF overlaps within 0.005, first-peak positions within 0.02 Å, and the
  Ge/Sb/Te mean frequencies within 0.1 THz (≤ 3%).
- **Structure agrees closely except in am_c10's second shell.** RDF R is 0.05–0.07 in seven phases, as for nozbl_paw.
  In am_c10 it is 0.091 (nozbl_paw 0.071, seed spread 0.006): Allegro's second-neighbour peak (3.5–4.7 Å) is lower
  and shifted outward relative to DFT's (`figures/am_c10.png`); the first peak and the C-bond shoulder at ~2.0 Å match
  as well as nozbl_paw's. In the crystals the first peak is 3–11% taller than DFT's, as for nozbl_paw.
- **Ge/Sb/Te vibrations are a little soft in the amorphous cells** (mean frequencies 1–11% below DFT, most for Sb in
  am_c10, 2.50 against 2.80 THz), and within 0–5% in the crystals: the same pattern as nozbl_paw.
- **Trigonal GST has the same wrong shape in its main band:** a sharp Ge/Te peak near 2.9 THz where DFT has a broad
  2.6–3.4 THz band (`figures/hex_gst.png`); lowest VDOS overlap, 0.87.
- **C vibrations agree least (overlap 0.49–0.72),** with the C bands in the right places and individual peaks
  shifted; in am_c10 the C mean frequency is 15% above DFT's (17.3 against 15.1 THz). cub_c1's lower C overlap (0.49
  against nozbl_paw's 0.66) is noise: the cell has 2 C atoms, and its three seeds give 0.28, 0.58 and 0.62.

## Effect of the relaxation (`phases_relaxation.txt`, `figures/relaxation_pe.png`)
The amorphous cells relax less during the standard window than with nozbl_paw: `dPE_prod` (the mean of the last 2 ps
minus the first 2 ps) is −0.006 to −0.011 eV/atom (nozbl_paw −0.010 to −0.014), and −0.0015 to −0.005 in the `_eq25`
window 20 ps later. The crystals drift by less than 0.001.

Paired by seed, the later window changes (mean differences; the spread between seeds of the standard runs in brackets):

| phase | RDF R | ADF overlap | VDOS overlap | ⟨ν⟩ Ge / Sb / Te (THz) | C VDOS overlap |
|---|---|---|---|---|---|
| am_gst | −0.003 [0.002] | −0.005 [0.009] | −0.003 [0.002] | −0.05 / −0.05 / −0.01 | — |
| am_c1 | +0.001 [0.014] | −0.008 [0.013] | +0.005 [0.001] | +0.07 / +0.02 / +0.03 | −0.008 [0.057] |
| am_c5 | +0.006 [0.012] | −0.005 [0.008] | +0.007 [0.010] | +0.07 / +0.05 / +0.03 | +0.001 [0.018] |
| am_c10 | −0.009 [0.006] | −0.010 [0.009] | −0.008 [0.006] | +0.07 / +0.03 / +0.05 | −0.038 [0.010] |

Every Ge/Sb/Te metric moves by about the seed spread or less, as for nozbl_paw. The exception is C in am_c10: the
later window raises ⟨ν_C⟩ by 1.4 THz (paired std 1.0; 18.6 ± 0.9 against 17.3 ± 0.1), further from DFT, and with it
the total ⟨ν⟩ by 0.33 THz. With 16 C atoms per cell the seeds scatter (+2.5, +0.6 and +1.0 THz), but all three move the same way. **No conclusion above changes;** the standard window, the one DFT used, stays the main
comparison.

## Caveats
The caveats of `../nozbl_paw/RESULTS.md` apply unchanged, as they concern the DFT references and the method: the two
Sb–Te cutoffs of the DFT ADF files (same choice per phase here, `adf_sbte`; am_gst again has 19% fewer angles than
its DFT file, `adf_count_ratio` 0.81), the training-data overlap (these DFT-MD phases are in `cgst_train_paw.xyz`,
so this tests reproduction of training phases), the 6 Å RDF range, and the one DFT trajectory per phase (whose noise
is not known; the ± are Allegro's seeds only).

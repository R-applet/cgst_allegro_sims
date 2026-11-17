# Phases: Allegro vs DFT-MD in the DFT cells at 300 K

Short NVT runs of the potential in the 8 cells that were simulated with DFT-MD at 300 K (amorphous GST + 0, 1.4, 5.3
and 10 at.% C; rocksalt and trigonal GST + 0 and 1.4% C; 144–160 atoms), compared with DFT on the same cell, volume,
temperature, timestep and window: the radial distribution function (RDF), the bond-angle distribution (ADF) and the
vibrational density of states (VDOS), total and per species. Results per potential:
`results/<MODEL_ID>/RESULTS.md`.

## Layout
- `structures/`: the 8 cells as LAMMPS data files (`convert_dft_cells.py`; the table of cells in its `README.md`).
- `dft/<phase>/`: the DFT references (`make_dft_refs.py`, run once; tracked): `rdf.txt`, `adf.txt`,
  `vdos_species.txt` (the DFT per-atom DoSPT DOS summed by species), `dospt_input.txt`, `SOURCES.txt` (paths and
  sha256 in `$DFT_PHASES`, `common/model.sh`).
- `in.phases`: velocities at `TEMP`, Nosé–Hoover NVT, `EQ_PS` of equilibration, then `PROD_PS` dumped every step
  (unwrapped positions and velocities, 8 decimals; `thermo.dat` every 100 steps).
- `params/<MODEL_ID>.sh`: `PHASES`, `NREP`, `TEMP`, `DT`, `EQ_PS`, `PROD_PS`, `TDAMP_PS`. Every value is set by the DFT
  reference (300 K, 1 fs, 5 ps discarded, 20 ps analysed), so a new potential copies the file unchanged. `DT` overrides
  the model's production timestep for this study only.
- `submit.sh`: the runs as a job array, index i → phase `PHASES[i / NREP]`, replica `i % NREP + 1`, velocity seed
  `1009 (i + 1) + 7`; run directory `runs/<MODEL_ID>/<phase>[_<TAG>]_r<k>/`.
- `submit_analysis.sh`: `analysis/phases_compare.py analyze` on every finished run (4 at a time), the `dft-check`
  validation, then `compare` → `results/<MODEL_ID>/` (tables, per-phase figures and `figures/summary.png`).

## Method
- **Cells.** The DFT box, tilts and atom order, so the per-atom DFT DOS maps onto Allegro's atoms; fixed volume.
- **MD.** 300 K, 1 fs, Nosé–Hoover with 0.1 ps damping. The first 5 ps are discarded and the next 20 ps (20000
  frames) analysed, as for the DFT trajectories. 3 seeds per phase give Allegro's spread; DFT has one trajectory
  per phase.
- **RDF.** Total g(r) on each DFT file's grid, normalized by N² as the DFT files are (pairs over the 27 neighbouring
  images; every 10th frame). Misfit R over 1.5–6 Å (the amorphous DFT files run to 10 Å, past half their box) and
  the first peak's position and height.
- **ADF.** At each atom, the angle between every pair of its bonds, as OVITO's BondAnalysis does, with the DFT files'
  bond cutoffs (`ADF_CUTOFFS` in `analysis/phases_compare.py`). The DFT files used Sb–Te 3.2 Å for some phases and
  3.4 Å for others, so each ADF is computed with both and compared with the variant whose angles per frame match the
  DFT file's. Overlap, peak angle, and the ratio of angles per frame (a coordination check).
- **VDOS.** DoSPT (Caro's 2PT code, the non-orthogonal-cell fork; built by `analysis/build_dospt.sh`) with the DFT
  settings: velocities estimated from the positions, one group per atom, summed by species. Both sides smoothed
  alike and normalized to unit area over 0–60 THz; overlap and mean frequency, total and per species.
- **Checks** (every potential): DoSPT on the dumped exact velocities for two runs (`EXACT_V`; must give overlap ≈ 1),
  DoSPT's cell against the box in every run (`analyze` stops on a mismatch), and `dft-check`, which runs the RDF/ADF code on the hex_gst DFT trajectory and must reproduce its DFT files.
- **Relaxation check.** The amorphous cells relax during the window (PE drift ~−0.01 eV/atom over 20 ps for
  nozbl_paw). Runs tagged `eq25` repeat them with the same seeds and `EQ_PS=25`, and `compare` pairs them by seed
  (`phases_relaxation.txt`).

## Running
```
cd phases
sbatch --array=0-23 submit.sh                                       # 8 phases x 3 seeds, ~1.5 min each on an A30, 1–1.7 on a perc A100
sbatch --array=0-11 --export=ALL,EQ_PS=25,TAG=eq25 submit.sh       # amorphous phases, longer equilibration
sbatch submit_analysis.sh                                           # after both; ~25 min on 16 CPUs
```
Each run's dump is ~260 MB (9.4 GB for the 36 runs of nozbl_paw); `runs/` is not tracked.

Caveat for every potential: the DFT-MD of these phases is in the training data (`cgst_train_paw.xyz`), so this tests
how the potential reproduces its training phases, not a prediction.

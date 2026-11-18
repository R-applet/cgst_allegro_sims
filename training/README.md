# Training: data, configs and scripts for the PAW-cleaned Allegro potentials

Everything needed to retrain the Allegro potentials used in this record: the training and test sets, the
nequip/Allegro configs and submit scripts for each model, and the scripts that built and cleaned the data.
Each folder's best checkpoint is tracked (Checkpoints, below); compiled `.pt2` files are not (`models/provenance.md`).

## Data (`data/`)

| file | frames | what |
|---|---|---|
| `cgst_train_paw.xyz.xz` | 17,687 | training + validation set (the configs split it 80/20, seed 456) |
| `cgst_test_paw.xyz.xz` | 2,403 | test set (`TESTSET`) |
| `dimers_atoms_nsp_Eform.xyz` | 484 | the non-spin isolated atoms and dimers already contained in the training set, also kept separately |
| `cgst_train_paw_removed.csv`, `cgst_test_paw_removed.csv` | 84, 11 | frames removed by the PAW-overlap filter, with their offending contacts |
| `SHA256SUMS` | | sha256 of the uncompressed files |

Decompress next to the configs' expected path: the configs read `../../CGST/cgst_train_paw.xyz` (models under
`zbl_updated/`) or `../cgst_train_paw.xyz` (models under `CGST/`), i.e. `/depot/prism/data/rushik/CGST/`.
`xz -dk cgst_train_paw.xyz.xz && sha256sum -c SHA256SUMS`.

**Energy reference.** Labels are formation energies, `energy = E_DFT(free, TOTEN) − Σ n_i μ_i`, with the bulk
references of `rapplet/cgst_ref_structs` (recovered exactly from `rapplet/cgst-vasp-data/xyz_files/all/{Etot,Eform}`):
μ_Ge −4.783860, μ_Sb −4.571496, μ_Te −3.136069, μ_C −9.298617 eV/atom. DFT: VASP PBE PAW, 600 eV, DFT-D2 (`IVDW=10`),
`ISMEAR=0`, `SIGMA=0.05`, non-spin-polarized. Forces in eV/Å, stress in eV/Å³ (ASE sign convention).

**Per-type energy shifts** (every config): isolated non-spin atom minus μ, in the same reference:
Ge 4.70127, Sb 4.47921, Te 3.04859, C 9.21423 eV. These fix the dissociation limit; without them the
pre-PAW models put separated atoms at the crystal energy and vaporized instead of melting.

**How the set was built** (from rapplet's `cgst_train.xyz`, 17,290 frames):
1. `+` 484 non-spin isolated-atom and dimer frames (`scripts/make_inputs.py`, `run_dirs.sh`, `build_dimer_xyz.py`):
   dimers from 65 % of the summed PAW core radii (1.58 Å Ge/Sb/Te, 1.31 Å with C, 1.03 Å C–C) to 5 Å, plus
   points beyond 5 Å within 0.05 eV of the atom limit (the non-spin tail is still bound at 6 Å, which a 6 Å model
   cannot represent). Energies in `scripts/results.json`.
2. `−` frames 4680, 5017 (Ge–Ge contacts at 0.40/0.43 Å) and 7160 (duplicate of two test frames).
3. `−` every frame with a pair closer than 65 % of the summed PAW core radii (`scripts/filter_paw_contacts.py`;
   dimer and atom frames exempt): 84 training frames, 11 test frames.

## Configs (`configs/<training directory>/`)

Each folder: `config_paw.yaml` (as submitted), `config_resolved.yaml` (hydra-resolved), `submit_paw.sh`, `train.log`.
All three are trained **from scratch** on the same data with identical settings except the short-range term:
`allegro.model.AllegroModel`, float64, cutoff 6.0 Å, 1 layer, `l_max` 3, 128 scalar / 16 tensor features,
energy + force + stress loss (coeffs 1/1/1), EMA 0.999, Adam lr 1e-3, `ReduceLROnPlateau` (factor 0.5, patience 30,
threshold 1e-4), batch 1, 2 GPUs (DDP), `max_time` 2 d 23 h, best checkpoint by validation force RMSE.

| folder (training directory) | `MODEL_ID` | short range | environment | best epoch | val F RMSE (eV/Å) | test E / F RMSE |
|---|---|---|---|---|---|---|
| `nequip_no_zbl` | `nequip_no_zbl` | none | conda `allegro` (nequip 0.17.1, allegro 0.8.2) | 503 | 0.1219 | 6.9 meV/atom / 0.120 eV/Å |
| `rushik_zbl_pairwise` | — | per-pair ZBL at the data edge, 1.15–1.76 Å, p = 2 | `zbl_updated/venv` (modified nequip 0.18.0, allegro 0.8.3) | 496 | 0.1228 | 7.3 / 0.122 |
| `nequip_zbl` | — | ZBL for all pairs to r_max 6 Å, p = 2 | conda `allegro` | 507 | 0.1214 | 7.0 / 0.120 |

Per-pair ZBL cutoffs (`per_edge_type_cutoff`) need the modified nequip in `zbl_updated/` (stock 0.17.1 lacks them).

`rushik_zbl_pairwise` was trained as `rushik_zbl_dataedge` (its hydra run name, `submit_paw.sh` job name and
`train.log` paths keep that name); renamed here 2026-11-18.

## Checkpoints

Each `configs/<training directory>/best.ckpt` is that run's best checkpoint (lowest validation force RMSE);
sha256 in `CHECKPOINTS.sha256`. They are tracked through an exception in the top-level `.gitignore`
(`*.ckpt` stays ignored everywhere else).

| folder | `MODEL_ID` | best epoch | sha256 (first 16) |
|---|---|---|---|
| `nequip_no_zbl` | `nequip_no_zbl` | 503 | `ed645c56ddeb3311` |
| `rushik_zbl_pairwise` | — | 496 | `4e45d86354fe6157` |
| `nequip_zbl` | — | 507 | `6feb183a45a9c2e4` |

The `nequip_no_zbl` hash matches `models/provenance.md`.

Loading: `nequip.ase.NequIPCalculator._from_saved_model(ckpt)` or `nequip-compile` (see `models/compile_model.sh`).
Per-pair ZBL models need the modified nequip from `zbl_updated/` on `PYTHONPATH`; stock nequip 0.17.1 is enough for
`nequip_no_zbl` and `nequip_zbl`. Compiling reads one training frame through the checkpoint's relative data path, so
run it from a directory where `../../CGST/cgst_train_paw.xyz` (or `../cgst_train_paw.xyz`) resolves.

## Notes

- Never resume or fine-tune on 2 GPUs: twice (ModelFromCheckpoint, and `++ckpt_path` resume) the weights went NaN
  within the first steps. From scratch on 2 GPUs, or continuation on 1 GPU, has always worked.
- In bulk (test set, liquid/amorphous DFT frames, melt-quench) the models are equivalent; they differ only
  below ~1.6 Å (dimer scans), where there is no DFT data.

# Model registry and provenance

The potentials this project runs, each named after its training folder (`training/configs/<MODEL_ID>/`, which holds
the config, training log and best checkpoint), with the compiled files per node type (`common/model.sh` names them;
`common/defaults.sh` picks the file for the node). The compiled `.pt2` files are tracked in `models/`; their hashes
are here (check with `sha256sum`). The three models are trained from scratch on the same PAW data with identical settings except the short-range
term (`training/README.md`).

| MODEL_ID | Type | Short range | Checkpoint (sha256) | Compiled files | Status |
|---|---|---|---|---|---|
| `nequip_no_zbl` | Allegro 0.8.2 (stock nequip 0.17.1) | none | `ed645c56…bfcc` | A30, `.G`, `.N`, `.K` (validated) | default `MODEL_ID`; formerly `nozbl_paw` |
| `nequip_zbl` | Allegro 0.8.2 (stock nequip 0.17.1) | ZBL for all pairs to r_max 6 Å | `6feb183a…aee3` | `.G`, `.N`, `.K` (validated; no A30 file) | gate, smoke and dt passed 2026-11-18 |
| `rushik_zbl_pairwise` | Allegro 0.8.3 (modified nequip 0.18.0, `zbl_updated`) | per-pair ZBL at the data edge, 1.15–1.76 Å | `4e45d863…57e4` | `.G`, `.N`, `.K` (validated; no A30 file) | gate, smoke and dt passed 2026-11-18 |

## nequip_no_zbl

| | |
|---|---|
| Name | `nozbl_paw` until 2026-11-18, renamed to its training folder's name (`MODEL_ALIASES=nozbl_paw` in `common/model.sh`): logs, `lmp_inputs/` records and raw test outputs written before then name `nozbl_paw` and `models/nozbl_paw*.nequip.pt2`. Same checkpoint and the same compiled files, renamed (the hashes below are unchanged) |
| Source checkpoint | `/depot/prism/data/rushik/CGST/nequip_no_zbl/outputs/2026-11-05/19-04-55/best.ckpt` (saved 2026-11-08 13:37); in the repo as `training/configs/nequip_no_zbl/best.ckpt` (`CKPT`; until 2026-11-18 a local copy `models/nozbl_paw.ckpt`, identical) |
| sha256 (checkpoint) | `ed645c56ddeb3311789e12f6d7421462978beb292b0f3b5ce30afdbfaf2bbfcc` |
| Training config | `.../nequip_no_zbl/config_paw.yaml` (resolved: `outputs/2026-11-05/19-04-55/.hydra/config.yaml`); `allegro.model.AllegroModel`, float64, `cutoff_radius` 6.0 Å, `num_layers` 1, `l_max` 3, 128 scalar / 16 tensor features, energy + force + stress loss, EMA 0.999 |
| Training data | `../cgst_train_paw.xyz` (the PAW set of every current model, `training/data/`), test set `../cgst_test_paw.xyz` (= `TESTSET`) |
| Training run | nequip 0.17.1, allegro 0.8.2, torch 2.8.0 (`train.log`); started 2026-11-05 19:04, stopped by `max_time` (2 d 23 h) at epoch ~538 of `max_epochs` 1500. `best.ckpt` = lowest validation metric |
| Types | `Ge Sb Te C` → LAMMPS types 1–4 (`chemical_symbols` order) |
| No ZBL | no short-range repulsion term: close contacts in hot liquids are possible; `analysis/mq_summary.py` reports the closest pair distances per run (`rmin_*`) |
| Compile | the container's own nequip/allegro are the training versions, so `MODEL_SRC` is empty; `TRAIN_DIR` is `.../nequip_no_zbl`, where the checkpoint's relative `../cgst_train_paw.xyz` resolves |
| Not used | `.../nequip_no_zbl/0718_nequip_no_zbl.nequip.pt2`: compiled 2026-07-18 from an older run on the pre-PAW data (`config.yaml`, `outputs/2026-07-15`) |

Compiled files (`models/compile_model.sh` on a node of each type, from the same checkpoint, as `nozbl_paw*.nequip.pt2`; renamed
2026-11-18; the compile logs were removed then, the hashes are below):

| file | compiled on | used on | sha256 | validated |
|---|---|---|---|---|
| `nequip_no_zbl.G.nequip.pt2` | a100-40gb gilbreth-g008, 2026-11-13 (job 12358491) | a100-40gb g-nodes | `f76aeea05254960c98abd3f4c27dbecc15b628627c0258ff360e24dcfc4e037d` | `tests/model_check` (job 12358679, g000): vs checkpoint max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.5e-11 eV/Å, max \|ΔP\| 0.005 bar; `tests/model_select` (job 12358680, g000): selected and \|ΔE\| = 0 |
| `nequip_no_zbl.N.nequip.pt2` | a100-40gb gilbreth-n006, 2026-11-13 (job 12358492) | a100-40gb n-nodes | `a9933e81fcce76eccefb0223bf316df89d58021e254d5678d84a5c7e955dcf5f` | `tests/model_select` (job 12358681, n011): selected, max \|ΔE\| = 0 vs the G file on the 13 model_check frames |
| `nequip_no_zbl.K.nequip.pt2` | a100-80gb gilbreth-k050, 2026-11-14 (job 12383791, account `alta`) | a100-80gb k-nodes | `d78970fd7c54059a5622f453723bb3082135218db2df332061b42ad14ec57fea` | `tests/model_select` (job 12383792, k050): selected, max \|ΔE\| = 0 vs the G file on the 13 model_check frames |
| `nequip_no_zbl.nequip.pt2` | a30 gilbreth-b013, 2026-11-13 (job 12359234, account `strachan`) | a30 b-nodes (d-nodes: same file, not yet checked there) | `6e90500833de32ac1c3bfdb6512ab0ea6ec922aeee416775687432c1cd8943e5` | `tests/model_select` (job 12384204, b003): selected, max \|ΔE\| = 0 vs the G file on the 13 model_check frames |

All four files (A30, G, N, K) are the same model: identical energies (max |ΔE| = 0) on the 13 model_check frames.
The K file serves the a100-80gb k-nodes of the `alta` account (36 GPUs; no a100-40gb), where the A30 build died with
`Illegal instruction` in Part 1; i-nodes (also a100-80gb) still have no file. They differ in
bytes, as AOTInductor output depends on the build machine.

First accuracy look (`tests/model_check`, the same 13 DFT test frames, 144–768 atoms, 0–77 C): checkpoint energy vs
DFT, RMS 5.4 meV/atom (mean |error| 4.7, max 10.4). `stress_parity`, `am_eos` and the other tests:
`tests/results/nequip_no_zbl/RESULTS.md` (all pass; pressure RMSE 1.65 kbar; 2 fs timestep).

## nequip_zbl

| | |
|---|---|
| Checkpoint | `training/configs/nequip_zbl/best.ckpt` (best epoch 507), sha256 `6feb183a45a9c2e4e1e64944599fe9c6584de85632d1ccdd51d4e0bb6ddeaee3` |
| Training | `training/configs/nequip_zbl/` (`config_paw.yaml`, `train.log`); nequip 0.17.1 / allegro 0.8.2 = the container's |
| Short range | ZBL for every pair out to r_max (6 Å), p = 2 |
| Compile | `MODEL_SRC` empty; `TRAIN_DIR=/depot/prism/data/rushik/CGST/nequip_zbl`, where the checkpoint's relative `../cgst_train_paw.xyz` resolves |

Compiled files (`models/compile_model.sh` with `MODEL_ID=nequip_zbl` on a node of each type, 2026-11-18; logs
`models/slurm-<job>.out`; the checkpoint loads with a torch-version warning only):

| file | compiled on | used on | sha256 | validated |
|---|---|---|---|---|
| `nequip_zbl.G.nequip.pt2` | a100-40gb gilbreth-g002 (job 12429600) | a100-40gb g-nodes | `7a130d6344d54b9f5990d4d21cdacdfbd0db7660199d020e4715f5f0b8c4f485` | `tests/model_select` (job 12430329, g000): selected, max \|ΔE\| = 0 vs `model_check` (job 12430328, N: vs checkpoint max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.2e-11 eV/Å) |
| `nequip_zbl.N.nequip.pt2` | a100-40gb gilbreth-n009 (job 12429601) | a100-40gb n-nodes | `52b0f926eabda7432706d43e905fc9dec999872af74b862bc3d5acf6220722a0` | `tests/model_check` (job 12430328, n012) and `tests/model_select` (job 12430330, n012): max \|ΔE\| = 0 |
| `nequip_zbl.K.nequip.pt2` | a100-80gb gilbreth-k038, account `alta` (job 12429602) | a100-80gb k-nodes | `ea92342148fb6423f423e80324b22c70fe5852eca444b284f055e2527dc5ebac` | `tests/model_select` (job 12430331, k028): selected, max \|ΔE\| = 0 |


## rushik_zbl_pairwise

| | |
|---|---|
| Checkpoint | `training/configs/rushik_zbl_pairwise/best.ckpt` (best epoch 496), sha256 `4e45d86354fe6157a125a9941e3a71425ebcc64b66b783af00d70c01ce7257e4` |
| Training | trained as `rushik_zbl_dataedge` (`/depot/prism/data/rushik/zbl_updated/rushik_zbl_dataedge`); `training/configs/rushik_zbl_pairwise/`; modified nequip 0.18.0 / allegro 0.8.3 |
| Short range | per-pair ZBL (`per_edge_type_cutoff`) at the edge of the training data, 1.15–1.76 Å, p = 2 |
| Compile | the modified sources `MODEL_SRC=/depot/prism/data/rushik/zbl_updated` on `PYTHONPATH` (the container's nequip 0.17.1 lacks per-pair cutoffs), from `TRAIN_DIR=$MODEL_SRC/rushik_zbl_dataedge`, where `../../CGST/cgst_train_paw.xyz` resolves; `NEQUIP_FLOAT64_MODEL_TOL=1e-10` |

Compiled files (`models/compile_model.sh` with `MODEL_ID=rushik_zbl_pairwise` on a node of each type, 2026-11-18; logs
`models/slurm-<job>.out`; the checkpoint loads with a torch-version warning only):

| file | compiled on | used on | sha256 | validated |
|---|---|---|---|---|
| `rushik_zbl_pairwise.G.nequip.pt2` | a100-40gb gilbreth-g002 (job 12429603) | a100-40gb g-nodes | `33fcae9062562096c5b4e1fe76525b8e80a30e11a69283e046f56202cb0ca67d` | `tests/model_select` (job 12430418, g003): selected, max \|ΔE\| = 0 vs `model_check` (job 12430417, N: vs checkpoint max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 2.3e-11 eV/Å) |
| `rushik_zbl_pairwise.N.nequip.pt2` | a100-40gb gilbreth-n002 (job 12429604) | a100-40gb n-nodes | `d7f6582f15c70515d993a8bf740d47bf4eda24a274e0814772e483c47355209e` | `tests/model_check` (job 12430417, n012) and `tests/model_select` (job 12430419, n012): max \|ΔE\| = 0 |
| `rushik_zbl_pairwise.K.nequip.pt2` | a100-80gb gilbreth-k039, account `alta` (job 12429605) | a100-80gb k-nodes | `6c5b4e4e01979d49fa0b8bed86146661edcb7307d4ba88fca9c279df11011d68` | `tests/model_select` (job 12430420, k011): selected, max \|ΔE\| = 0 |


## Notes for every model

- An AOT-compiled model's host code runs only on the CPU type it was compiled on; elsewhere it dies with `Illegal
  instruction` in the model loader (`tests/RESULTS.md`, Environment). Hence one file per node type.
- AOTInductor output is not byte-reproducible, so a hash identifies a file, not the model; a recompile gives identical
  energies (`tests/compile_check`).
- A checkpoint saved by torch 2.12 (the `zbl_updated` training environment) loads and compiles in the container's
  torch 2.8 with version warnings only; `tests/model_check` confirms the compiled file against the checkpoint.
- On perc g-nodes a compile or LAMMPS job can die in `MPI_Init` (PMIx `gds_ds12` lock); `sbatch
  --export=ALL,PMIX_MCA_gds=hash` avoids it (`RUNBOOK.md`).

## Container (every model)

| | |
|---|---|
| File | `/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif` (owner desai224; on the prism depot) |
| Size, mtime | 10,896,695,296 bytes, 2026-04-01 11:45:54 −0400 |
| sha256 | `31a7c4c15321b3f63e105b717c8eac33940f10bab2fb5d84966534dc70e58c23` (`lammps_debug.sif.sha256`, 2026-11-06) |
| `lmp` binary | `/usr/local/bin/lmp`, BuildID `c49ff0e199c9e191b702e457413f4b3d7187986c`, 611 MB, with debug_info |

**It is an unoptimized ("debug") build of the LAMMPS/Kokkos host code.** The DWARF producer strings of the five
compilation units checked read `GNU C++17|C++20 12.3.0 … -march=x86-64 -g …` with no `-O` flag, which in GCC means `-O0`.
This costs nothing measurable here: the model evaluation (libtorch/AOTInductor, built separately) dominates
(Pair = 95–98% of the run time), and `lammps_stable.sif` runs the same benchmark at the same speed with identical
energies (`tests/RESULTS.md`, 1f). It is kept because the reference runs used it.

`lammps.def.reference` is the recipe next to the image (2026-04-27). It is **not** this image's exact recipe: it is
newer than the image and adds `PKG_SHOCK`, which this image lacks. It does show the intended build: `CMAKE_BUILD_TYPE=Debug`
(matching the `-g`-only flags), `Kokkos_ARCH_AMPERE80`, `Kokkos_ARCH_HOSTARCH`, and pair_nequip_allegro from git `HEAD`.

**Before trusting new results, check the image hash** (`sha256sum -c models/lammps_debug.sif.sha256`).
The file is in another user's directory and could be rebuilt in place. A changed hash means re-running
`tests/model_check` and `tests/smoke` before continuing.


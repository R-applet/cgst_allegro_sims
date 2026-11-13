# Model registry and provenance

Every potential this project has run, with the checkpoint it came from and the compiled files per node type
(`common/model.sh` names them; `common/defaults.sh` picks the file for the node). Compiled `.pt2` files and local
checkpoint copies are not tracked by git; their hashes are here.

| MODEL_ID | Type | Short range | Training data | Checkpoint (sha256) | Compiled files | Status |
|---|---|---|---|---|---|---|
| `run5_ep301` | Allegro (nequip/allegro with per-pair ZBL, `zbl_updated`) | per-pair ZBL | `CGST/cgst_train_paw.xyz` | `run5_ep301.ckpt` (`b6ae59f2…96b1`) | `.pt2`, `.G`, `.N` | archived, tag `run5_ep301-final` |
| `nozbl_paw` | Allegro 0.8.2 (stock nequip 0.17.1) | none | `CGST/cgst_train_paw.xyz` | `nozbl_paw.ckpt` (`ed645c56…bfcc`) | `.G`, `.N` (validated; A30 file not yet built) | in progress (default `MODEL_ID`) |
| (second potential) | — | — | — | — | — | to be provided |

## nozbl_paw

| | |
|---|---|
| Source checkpoint | `/depot/prism/data/rushik/CGST/nequip_no_zbl/outputs/2026-11-05/19-04-55/best.ckpt` (saved 2026-11-08 13:37), copied to `models/nozbl_paw.ckpt` on 2026-11-13 so a resumed training run cannot change it |
| sha256 (checkpoint) | `ed645c56ddeb3311789e12f6d7421462978beb292b0f3b5ce30afdbfaf2bbfcc` |
| Training config | `.../nequip_no_zbl/config_paw.yaml` (resolved: `outputs/2026-11-05/19-04-55/.hydra/config.yaml`); `allegro.model.AllegroModel`, float64, `cutoff_radius` 6.0 Å, `num_layers` 1, `l_max` 3, 128 scalar / 16 tensor features, energy + force + stress loss, EMA 0.999 |
| Training data | `../cgst_train_paw.xyz` (the same PAW set as run5_ep301), test set `../cgst_test_paw.xyz` (= `TESTSET`) |
| Training run | nequip 0.17.1, allegro 0.8.2, torch 2.8.0 (`train.log`); started 2026-11-05 19:04, stopped by `max_time` (2 d 23 h) at epoch ~538 of `max_epochs` 1500. `best.ckpt` = lowest validation metric |
| Types | `Ge Sb Te C` → LAMMPS types 1–4 (`chemical_symbols` order, as for run5_ep301) |
| No ZBL | no short-range repulsion term: close contacts in hot liquids are possible; `analysis/mq_summary.py` reports the closest pair distances per run (`rmin_*`) |
| Compile | the container's own nequip/allegro are the training versions, so `MODEL_SRC` is empty; `TRAIN_DIR` is `.../nequip_no_zbl`, where the checkpoint's relative `../cgst_train_paw.xyz` resolves |
| Not used | `.../nequip_no_zbl/0718_nequip_no_zbl.nequip.pt2`: compiled 2026-07-18 from an older run on the pre-PAW data (`config.yaml`, `outputs/2026-07-15`) |

Compiled files (`models/compile_model.sh` on perc, from `models/nozbl_paw.ckpt`; the logs, `models/slurm-<job>.out`,
print the hash):

| file | compiled on | used on | sha256 | validated |
|---|---|---|---|---|
| `nozbl_paw.G.nequip.pt2` | a100-40gb gilbreth-g008, 2026-11-13 (job 12358491) | a100-40gb g-nodes | `f76aeea05254960c98abd3f4c27dbecc15b628627c0258ff360e24dcfc4e037d` | `tests/model_check` (job 12358679, g000): vs checkpoint max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.5e-11 eV/Å, max \|ΔP\| 0.005 bar; `tests/model_select` (job 12358680, g000): selected and \|ΔE\| = 0 |
| `nozbl_paw.N.nequip.pt2` | a100-40gb gilbreth-n006, 2026-11-13 (job 12358492) | a100-40gb n-nodes | `a9933e81fcce76eccefb0223bf316df89d58021e254d5678d84a5c7e955dcf5f` | `tests/model_select` (job 12358681, n011): selected, max \|ΔE\| = 0 vs the G file on the 13 model_check frames |
| `nozbl_paw.nequip.pt2` | — | a30 b- and d-nodes | — | not built (A30 queue; RUNBOOK A2) |

Both A100 files are the same model: identical energies (max |ΔE| = 0) on the 13 model_check frames. They differ in
bytes, as AOTInductor output depends on the build machine (as for run5_ep301).

First accuracy look (`tests/model_check`, the same 13 DFT test frames, 144–768 atoms, 0–77 C): checkpoint energy vs
DFT, RMS 5.4 meV/atom (mean |error| 4.7, max 10.4), against 6.3 (5.5, 9.7) for run5_ep301. `stress_parity`, `am_eos`
and the other tests: `tests/results/nozbl_paw/RESULTS.md` (all pass; pressure RMSE 1.65 vs 2.60 kbar for
run5_ep301; 2 fs timestep).

## run5_ep301

`run5_ep301.nequip.pt2` and its G/N copies: the potential of every run up to tag `run5_ep301-final`.

| | |
|---|---|
| Source compiled file | `/depot/prism/data/rushik/zbl_updated/rushik_zbl_super_short/md_meltquench/run5_ep301.nequip.pt2` (copied 2026-11-06) |
| sha256 (compiled) | `0a1a1b31733501e9880723f01ca1092a5d26d78793ecd7b089b451c1ea1301b1` |
| Checkpoint | `.../md_meltquench/run5_ep301.ckpt`, sha256 `b6ae59f20a2fdcbbcb31a3f20a1728304b57b2f37f87f72d3c963d4f2c0596b1` |
| Training config | `.../rushik_zbl_super_short/config_ft51_paw.yaml` (fine-tune from `outputs/2026-10-22/09-32-54/best.ckpt`) |
| Training data | `/depot/prism/data/rushik/CGST/cgst_train_paw.xyz`, test set `cgst_test_paw.xyz` (the test set has C-doped cells up to 10 at.% C, e.g. 768-atom cells with 77 C) |
| Types | `Ge Sb Te C` → LAMMPS types 1–4 |
| Cutoff | 6.0 Å (`config_ft51_paw.yaml`: `cutoff_radius: 6.0`); per-pair ZBL short-range terms according to the reference submit script (not checked against the config) |
| Compiled for | `pair_allegro`, AOTInductor, CUDA, sm_80 (A30 and A100; not A10/H100) |
| Container | `/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif` (LAMMPS 30 Mar 2026, Kokkos 5.0.2, libtorch 2.8.0+cu126); see below |

The compiled model must come from the same container libtorch that runs it. The container's own nequip (0.17)
lacks the per-pair ZBL cutoffs, so compiling uses the modified `nequip`/`allegro` from
`/depot/prism/data/rushik/zbl_updated` on `PYTHONPATH`, and `NEQUIP_FLOAT64_MODEL_TOL=1e-10`.
`nequip-compile` must run from the training folder (`.../rushik_zbl_super_short`): it loads a sample frame through
the checkpoint's relative dataset path `../../CGST/cgst_train_paw.xyz`, which only resolves from there.
`compile_model.sh` reproduces the compile, for example for another GPU architecture. `tests/compile_check` confirmed
that its output gives identical energies to this file (max |ΔE| = 0 on 13 frames). The sha256 differs, because the
AOTInductor output is not byte-reproducible, so the hash above identifies this specific file, not the model.

`tests/model_check` confirms that this file reproduces the checkpoint's energies and forces (see `tests/RESULTS.md`).

### Compiled files per node type
An AOT-compiled model's host code runs only on the CPU type it was compiled on. On other CPUs it dies with
`Illegal instruction` in the model loader (`tests/RESULTS.md`, environment probe). `common/defaults.sh` picks the
file from the hostname when a job starts.

| file | compiled on | used on | sha256 | validated |
|---|---|---|---|---|
| `run5_ep301.nequip.pt2` | a30 b-node (reference run, 2026-11-05) | a30 b- and d-nodes (d000, d005: `tests/scaling`, 1d) | `0a1a1b31…01b1` | all of `tests/`, 1a–1i |
| `run5_ep301.G.nequip.pt2` | a100-40gb gilbreth-g000 (AMD EPYC 7662), 2026-11-06 | a100-40gb g-nodes | `94f52d392dedbaadad35efa74c30058a9700988986419db0616aa90ca6249b33` | `tests/a100_model` (g000); `tests/model_select` (g005) |
| `run5_ep301.N.nequip.pt2` | a100-40gb gilbreth-n019 (AMD EPYC 7413), 2026-11-06 | a100-40gb n-nodes | `4077268cb713995582f2d0a402bfecb8f9dcbbc4de75eb251c555b275fe819f4` | `tests/a100_model` (n019); `tests/model_select` (n003); also ran `tests/glass_relax` on n002 and n010 |

- All three are the same model: max |ΔE| = 0 on the 13 model_check frames. They are not byte-identical, because
  AOTInductor output depends on the build machine.
- All were compiled from the same checkpoint with `compile_model.sh`. G and N copies are from `tests/a100_model/`;
  the hashes were checked against those copies.
- a100-80gb (strachan's k- and i-nodes) has no compatible file yet. Build one there with `compile_model.sh` and add
  it to `common/defaults.sh`.

## Container (both models)

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


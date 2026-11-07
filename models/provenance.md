# Model provenance

`run5_ep301.nequip.pt2`: the production potential for every run in this project.

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

## Container

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


# rushik_zbl_super_short — fixes and reruns

Log of what was changed, why, and where the files are. Newest run at the bottom.

## 1. Diagnosis of the original model (`outputs/2026-07-12/19-11-03`)

Symptom: in NPT heating (300 → 1000 K, 0.2 K/ps, 10,000 atoms) the cell vaporized instead of melting.

- **No cohesive energy.** Labels are formation energies (DFT − Σnμ_bulk, crystal ≈ 0 eV/atom) and
  `per_type_energy_shifts` was unset, so isolated atoms sat at 0 — the same energy as the crystal.
  Expanding cubic GST, energy peaked at only 0.47 eV/atom (68 Å³/atom) and fell back to 0.
- **Short-range holes.** Dimer scans: Ge–Ge −30 eV at 0.43 Å, Ge–C −128 eV at 0.38 Å. The network
  learned to cancel ZBL to match a few frames with unphysical contacts (DFT ~10× softer than ZBL there).
  The model without ZBL (`CGST/nequip_no_zbl`) had no holes.
- Other issues found, not yet changed: stress weight 1.0 makes stress ~0.04% of the loss;
  ZBL envelope `polynomial_cutoff_p: 2` with ~1.3 Å cutoffs is weak everywhere.

Plots: `dimer_scan_super_short.png`, `dimer_binding_super_short.png`,
`../../CGST/nequip_no_zbl/dimer_scan_zbl_vs_no_zbl.png`.

## 2. New DFT: isolated atoms and dimers (`CGST/dft_atoms_dimers/`)

- Settings copied from `rapplet/cgst_ref_structs/*/INCAR` (PBE PAW 600 eV, DFT-D2 `IVDW=10`,
  `ISMEAR=0`, `SIGMA=0.05`, Γ only), non-spin-polarized to match the training data.
- 4 atoms + 526 dimer points over 10 pairs; shortest r = 65% of summed PAW core radii
  (1.58 Å Ge/Sb/Te pairs, 1.31 Å with C, 1.03 Å C–C). All converged.
- Bulk references μ recovered exactly (residual 5e-12 eV) from
  `rapplet/cgst-vasp-data/xyz_files/all/{Etot,Eform}`:
  Ge −4.783860, Sb −4.571496, Te −3.136069, C −9.298617 eV/atom.
- `build_dimer_xyz.py` → `dimers_atoms_nsp_Eform.xyz` (484 frames): all points to 5.0 Å plus
  farther points within 0.05 eV of the atom limit (the nsp tails are still 0.05–0.3 eV bound at
  6 Å, which a 6 Å-cutoff model cannot represent).

Plot: `CGST/dft_atoms_dimers/dimer_dft_nsp_vs_models.png`.

## 3. Run 2 — shifts + dimers, from scratch (`outputs/2026-10-22/09-32-54`, job 11986466)

- `config.yaml`: `per_type_energy_shifts: {Ge: 4.70127, Sb: 4.47921, Te: 3.04859, C: 9.21423}`
  (nsp isolated atom − μ); data `CGST/cgst_train_dimers.xyz` = `cgst_train.xyz` + the 484 frames.
- Result: cohesion fixed (expansion rises to 3.73 eV/atom, tensile at all expanded volumes);
  dimers match DFT from ~1.5 Å outward. But validation force RMSE blew up (3.53 eV/Å, max error
  2,359 eV/Å) — one frame, #5017 (Ge–Ge 0.43 Å), landed in the val split. Checkpoint selection
  froze at epoch 51 (`best.ckpt`); the run hit the 3-day limit at epoch 501 and the final model
  was lost. Ge–Ge hole deepened to −373 eV at 0.42 Å.

Plots: `dimer_old_vs_updated_full.png`, `dimer_old_vs_updated_binding.png`.

## 4. Run 3 — fine-tune from epoch 51, 2 GPUs (`outputs/2026-11-01/01-39-51`, job 12048329) — failed

- `config_ft51.yaml`: `ModelFromCheckpoint` from run 2's epoch-51 `best.ckpt`; data
  `CGST/cgst_train_clean.xyz` (frames 4680, 5017 and duplicate 7160 removed); lr 5e-4;
  scheduler `threshold` 0.2 → 1e-4; extra `latest.ckpt` saved every epoch; `max_time` 2d23h.
- Weights went NaN within the first 20 steps; ran 233 NaN epochs before being cancelled.
- Same config on 1 GPU (login-node A30) showed no NaN in 40 steps on the full data, so the
  2-GPU (DDP) + `ModelFromCheckpoint` combination is the suspected cause (not confirmed).

## 5. Run 4 — same fine-tune, 1 GPU (`outputs/2026-11-02/10-52-01`, job 12126581) — cancelled

- `config_ft51_1gpu.yaml` / `submit_ft51_1gpu.sh`: `devices: 1`, no DDP strategy.
- No NaN (759 logged steps finite). But epoch-0 validation force RMSE 1.93 eV/Å with max error
  1,594 eV/Å from frame #5143 (C–Te 0.43 Å). More such frames: #4630 (C–Te 0.49 Å),
  #11315 (Sb–Sb 0.70 Å). Cancelled after ~30 min to filter them all at once.

## 6. Run 5 — 1 GPU, PAW-filtered data (job 12127645) — submitted 2026-11-02

- `CGST/filter_paw_contacts.py` drops every frame with a pair closer than 65% of the summed PAW
  core radii (same cutoff as the DFT dimers; Atom_/Dimer_ frames exempt). Kept frames are copied
  byte-for-byte.
  - `cgst_train_clean.xyz` → `cgst_train_paw.xyz`: 17,771 → 17,687 (84 removed: 68 C10_runs,
    13 C5_runs, 3 C14). List: `cgst_train_paw_removed.csv`.
  - `cgst_test.xyz` → `cgst_test_paw.xyz`: 2,414 → 2,403 (11 removed). List: `cgst_test_paw_removed.csv`.
- `config_ft51_paw.yaml` / `submit_ft51_paw.sh`: identical to run 4 except the train/test files and
  W&B name `rushik_zbl_super_short_ft51_paw`.
- Still unchanged: ZBL cutoffs and `polynomial_cutoff_p: 2`, stress weight 1.0 (both fixed by the
  epoch-51 checkpoint).
- To check once running: no NaN in early steps; validation force RMSE close to training
  (~0.2 eV/Å) with no single error in the hundreds of eV/Å; then rerun the dimer and expansion
  scans (Ge–Ge hole should shrink or vanish).

Do not move `outputs/2026-10-22/09-32-54/best.ckpt` — runs 3–5 load it by path.

### Status 2026-11-03 (job 12127645, ~23 h in, epoch 100)

- No NaN (72k logged steps); `latest.ckpt` finite; lr still 5e-4 (no plateau cuts yet).
- Epoch 100: train force RMSE 0.155, val 0.149 eV/Å (run 1: 0.206); val per-atom energy RMSE
  0.023 eV; worst val force error 5–23 eV/Å per epoch (run 2: 2,359). Still improving ~0.01 eV/Å
  per 20 epochs.
- Pending: dimer + expansion scans on the newest checkpoint; NPT heating test.

### Physics checks on epoch-104 snapshot (2026-11-03)

Plots: `dimer_run5_ep104_full.png`, `dimer_run5_ep104_binding.png`, `expansion_run5_ep104.png`;
data: `dimer_scan_run5_ep104.npz`, `expansion_scan_run5_ep104.npz`.

- Short-range holes gone: every pair repulsive below 1.2 Å, no attractive force anywhere
  (Ge–Ge min was −373 eV at epoch 51, Ge–C −24 eV).
- Dimers vs DFT (r ≤ 5 Å) RMSE 0.11–0.50 eV per pair (epoch 51: 0.35–0.75); 3–5 Å tail error ≤ 0.46 eV.
- Expansion (cubic, hexagonal, amorphous GST): energy rises monotonically to 3.73 eV/atom; tension
  at every expanded volume (peak −8 GPa near 45 Å³/atom).
- Test set (`cgst_test_paw.xyz`), original model → epoch 104: energy RMSE 22.7 → 11.2 meV/atom,
  per-frame force RMSE 0.172 → 0.143 eV/Å, pressure RMSE 0.59 → 0.20 GPa. Pressure error is now
  uniform (−0.05 to −0.33 GPa by type; was −0.56 to +1.43). Remaining energy offset between
  crystal (+2.6 to +4.2 meV/atom) and hot/disordered frames (−4 to −11 meV/atom) is ~10–15 meV/atom.

## 7. NPT heating test, cubic GST (`md_npt_cubic_gst/`) — queued 2026-11-03

- Model: `run5_latest.ckpt` = run-5 `latest.ckpt` at epoch 121 (copied; the epoch-104 snapshot was
  in a temp folder that got cleared). CPU check: no attractive force below 1.6 Å for any Ge/Sb/Te
  pair; cubic expansion rises to 3.73 eV/atom.
- Structure: `build_cubic_gst.py` → `cubic_gst_7200.data`: ideal rocksalt Ge2Sb2Te5, 10×10×10 cells,
  a = 6.02 Å, Te on anion sites, Ge/Sb/vacancies 2:2:1 random on cation sites (seed 20261103);
  7200 atoms (1600 Ge, 1600 Sb, 4000 Te). 7200 not 10000 so the 2:2:5 ratio is exact.
- `in.heat_npt`: minimize → NPT 300 K/0 bar 50 ps → ramp 300→1500 K at 0.2 K/ps (6 ns) → 1500 K
  100 ps. 2 fs timestep, Nosé–Hoover (Tdamp 0.1 ps, Pdamp 1 ps, iso). Every 1 ps to
  `heat_npt.dat`: T, P, volume/atom, density, PE/atom, enthalpy/atom, MSD of Ge/Sb/Te.
  Trajectory every 50 ps, restart files every 100 ps.
- `submit_md.sh`: compiles the checkpoint with `nequip-compile --target pair_allegro` inside
  `lammps_debug.sif` (PYTHONPATH → modified nequip/allegro, since the container's nequip 0.17.1 lacks
  per-pair ZBL cutoffs), then runs LAMMPS (Kokkos, 1 A100).
- Jobs: smoke test 12151863 (`in.smoke`, 2+2 ps, 1 h) → full run 12152066 starts only if the
  smoke test exits cleanly (`afterok`).
- Read-out: melting = jump in V/atom and H/atom with Ge/Sb/Te MSD growing linearly;
  vaporization = volume running away. Superheating of a perfect crystal means melting may show
  well above the true Tm (~900 K).

### Update 2026-11-04: 2 GPUs, 2 K/ps

- Jobs 12151863/12152066 sat ~17 h behind the group's 7× A100-80GB cap (all in use); cancelled.
- Now on the `a30` partition (group cap 6, none in use), 2 GPUs: `srun --ntasks=2 … -k on g 2`.
- Ramp 300→1500 K at 2 K/ps = 600 ps (300,000 steps); trajectory every 10 ps (every 20 K).
  Time limit 1 day.
- Jobs: smoke test 12181514 → full run 12181515 (`afterok`).
- Two fixes before the smoke test passed: (1) `nequip-compile` must run from the training folder,
  because it loads a sample frame through the checkpoint's relative dataset path; (2) the thermo
  variables now use `compute pe`/`compute ke` (LAMMPS cannot evaluate the `pe`/`enthalpy` keywords
  inside a `fix print` variable). Compiled model: `md_npt_cubic_gst/run5_latest.nequip.pt2`.
- Smoke test 12181781 passed. Speed on 2× A30: 41 steps/s = 7.1 ns/day (295 katom-step/s), so the
  750 ps run (375,000 steps) takes ~2.6 h. Full run: job 12181782.

### Result 2026-11-05: heating run 12181782 completed (2 h 33 min on 2× A30)

Plot: `md_npt_cubic_gst/heat_npt_summary.png`; data: `md_npt_cubic_gst/heat_npt.dat`.
- **Melts, does not vaporize.** Sharp transition at a thermostat target of ~1070–1110 K: volume
  +0.75 Å³/atom (+2.4 %), enthalpy jump 0.184 eV/atom (17.8 kJ/mol of atoms), Ge/Sb/Te MSD goes
  from ~1 Å² to hundreds of Å² (Te MSD passes 10 Å² at 1096 K).
- Volume stays bounded: 34.3 Å³/atom (5.53 g/cm³) after 100 ps at 1500 K; maximum 34.5.
- Crystal density at 300 K 6.24 g/cm³; liquid 5.74 g/cm³ at 1200 K.
- Solid Cp 3.33 kB/atom, liquid 3.60 kB/atom.
- ~1096 K is ~1.2× the experimental Tm of GST (~900 K), the usual superheating of a perfect periodic
  crystal heated at 2 K/ps. A solid–liquid coexistence run is needed for the model's actual Tm.
- Training job 12127645 also finished (2 d 23 h). This MD used the epoch-121 checkpoint.

## 8. Same data/shift fixes applied to the other three models — submitted 2026-11-05 (from scratch)

New files in each folder: `config_paw.yaml` (copy of `config.yaml`) and `submit_paw.sh` (copy of
`submit_brice.sh`, same environment, runs `-cn config_paw.yaml`). Originals untouched.

| Folder | Environment | Model (unchanged) | Job |
|---|---|---|---|
| `zbl_updated/rushik_zbl_short` | `zbl_updated/venv` (modified nequip 0.18) | Allegro + per-pair ZBL, cutoffs 1.4–2.9 Å, p=2 | 12206770 |
| `CGST/nequip_no_zbl` | conda `allegro` (nequip 0.17.1) | Allegro, no ZBL | 12206771 |
| `CGST/nequip_zbl` | conda `allegro` (nequip 0.17.1) | Allegro + global ZBL to r_max = 6 Å, p=2 | 12206772 |

Changes in every `config_paw.yaml`: train `cgst_train_paw.xyz`, test `cgst_test_paw.xyz`;
`per_type_energy_shifts` Ge 4.70127, Sb 4.47921, Te 3.04859, C 9.21423; scheduler threshold 0.2 → 1e-4;
extra `latest.ckpt` every epoch; `max_time` 2d23h; W&B name `<folder>_paw`. Still 2 GPUs (DDP),
lr 1e-3, from scratch (no shift-trained checkpoint exists for these to fine-tune from).
Caveat: both ZBL models keep ZBL active inside the data range (bond lengths 2.4–3 Å), so the
network has to cancel ZBL there; check their dimer scans for holes when they finish.

## 9. Melt-quench (`md_meltquench/`) — submitted 2026-11-05, job 12210068

- Model: run-5 final best, epoch 301 (`run5_ep301.ckpt`, compiled in the job to `run5_ep301.nequip.pt2`).
- Start: `start_liquid_1500.data` = `md_npt_cubic_gst/final_1500.data` (liquid from the heating run).
- `in.meltquench`: NPT 1500 K 50 ps → cool 1500→300 K at 10 K/ps (120 ps) → NPT 300 K 100 ps,
  0 bar, 2 fs. Partial g(r) (all, Ge–Ge, Ge–Sb, Ge–Te, Sb–Sb, Sb–Te, Te–Te; 300 bins to 6 Å)
  averaged over the last 50 ps → `rdf_amorphous_300K.dat`. Thermo every 1 ps → `meltquench.dat`;
  trajectory every 5 ps → `traj.lammpstrj`; structures `liquid_1500_ep301.data`,
  `quenched_300.data`, `amorphous_300.data`.
- `submit_mq.sh`: same container/compile recipe as `md_npt_cubic_gst/submit_md.sh`, 2× A30. Expected ~1 h.

## 10. Melt-quench result and DFT check of the model's amorphous density (2026-11-06)

- 7200-atom melt-quench (job 12210068, 56 min): no crystallization; local structure plausible
  (Ge–Te 2.81 Å, Sb–Te 2.96 Å; CN Ge 4.46, Sb 3.85, Te 3.01; 9 % homopolar bonds) but the glass is
  **6.29 g/cm³, denser than the model's own cubic crystal (6.24)**; experiment ~5.9. Ge/Sb still
  diffuse at 300 K (MSD +1 Å² in 50 ps), Te frozen. Volume: the supercooled liquid contracts at
  0.0044 Å³/atom/K and crosses the crystal volume near 750 K, before the glass transition (~700 K),
  so a slower quench would make it denser, not less. RDF from trajectory:
  `md_meltquench/rdf_amorphous_300K_from_traj.dat` (the LAMMPS ave/time RDF window missed the run end).
- `md_mq144/`: three 144-atom melt-quenches (same protocol, 1 A30, job 12233213, 9 min) reproduce
  the density (6.29–6.31 g/cm³ at 300 K) → not a size effect. Snapshots at 1500, 1000, 800, 600, 300 K.
- `CGST/dft_amorphous_check/`: 18 VASP single points = 15 model snapshots + 3 labelled control frames
  (AM_GST_runs, GST_Melt_Quench test frames; LIQ_GST_runs training frame). Inputs = rapplet template
  INCAR (NELM 10→200, LCHARG/LWAVE off), data POTCARs, Γ-centred k at KSPACING 0.30 (2×2×2).
  `manifest.csv` holds the model's E and static P on every frame. Submit on the CPU cluster with
  `./submit_all.sh` (header from `dft_atoms_dimers/run_dirs.sh`).
- Read-out: controls must reproduce their labels; then if DFT static P on the 300–1000 K snapshots is
  clearly negative while the model's is near its NPT value, the model over-densifies the
  supercooled liquid/glass → add these frames to training.
- `nequip_zbl_paw` (job 12206772) failed: original config had invalid val metric keys
  (`per_atom_energy_mse`, `forces_mse`, `stress_mse`); removed in `config_paw.yaml`, resubmitted as 12232925.

## 11. Dimer + expansion scans: run 5 vs the three new models (2026-11-09)

Data `CGST/dft_atoms_dimers/scan_4models.npz` (GPU job `scan_job/`, 12299254); plots
`dimers_4models_{full,binding}.png`, `expansion_4models.png`. nequip_zbl = epoch ~460 (still training).
- Training/test: zbl_short and no_zbl both test E RMSE 6.9 meV/atom, F RMSE 0.120 eV/Å; val F
  0.1215 / 0.1219; nequip_zbl val F 0.1217 at epoch 460.
- Expansion: all four rise monotonically to 3.73 eV/atom (cohesion fine everywhere).
- Dimers vs DFT (trained points): new models 0.02–0.2 eV RMSE per pair (run 5: 0.07–0.26).
- Short range: only run 5 has a monotonic repulsive wall for every pair. New models have local dips
  inside the wall (no data below 1.58/1.31/1.03 Å after the PAW filter):
  zbl_short 16–223 eV deep at 0.74–1.0 Å, all ≥ 39 eV above the atom limit;
  no_zbl dips at ~0.67 Å, 28–64 eV above the limit, wall maximum only ~60–110 eV;
  zbl_6A (prelim.) Te–C hole to −232 eV at 0.56 Å behind a 36 eV barrier at 1.15 Å, Te–Te dip 144 eV.
  None reachable in thermal MD (barriers ≥ 30 eV), but they matter for collisions / high-energy events.

## 12. Fair comparison: zbl_super_short retrained from scratch (2026-11-09)

Run 5 (used for all MD so far) was fine-tuned from run 2's epoch-51 weights, which had trained on
data still containing the bad close-contact frames, so its clean short-range wall may be inherited.
The three other models were trained from scratch on the cleaned data. To compare like with like:
`config_paw.yaml` here = `rushik_zbl_short/config_paw.yaml` with only the super-short ZBL cutoffs
(0.7–1.45 Å) and W&B name `rushik_zbl_super_short_paw`; AllegroModel from scratch, lr 1e-3, 2 GPUs,
`cgst_train_paw.xyz`/`cgst_test_paw.xyz`, same shifts/threshold/latest-ckpt/max_time.
`submit_paw.sh` = same venv as `submit_brice.sh`.

## 13. Fifth model: ZBL at the data edge, p = 2 (2026-11-10, job 12306555)

`zbl_updated/rushik_zbl_dataedge/`: `config_paw.yaml` = `rushik_zbl_short/config_paw.yaml` with only the
per-pair ZBL cutoffs changed (and W&B name `rushik_zbl_dataedge_paw`). Cutoff = shortest training distance / 0.9:
1.76 Å Ge/Sb/Te pairs, 1.46 Å with C, 1.15 Å C–C; p = 2 like every other model, so ZBL is 0.3 % of bare
at the data edge and zero inside the data (nothing for the network to cancel), and 21–38 % of bare at
0.8–1.0 Å. From scratch, lr 1e-3, 2 GPUs, venv as in submit_brice.sh.

Comparison set (all from scratch, cleaned data, same shifts/training settings, p = 2 where ZBL is used):
nequip_no_zbl (no ZBL) | rushik_zbl_super_short (0.7–1.45 Å) | rushik_zbl_dataedge (1.15–1.76 Å) |
rushik_zbl_short (1.4–2.9 Å) | nequip_zbl (6 Å, all pairs).

## 14. 2026-11-11: super_short scratch run interrupted; archiving

- Job 12299293 (rushik_zbl_super_short from scratch) crashed after epoch 80 with a PermissionError
  writing its own output folder (transient /depot problem; folder writable again, /depot 98 % full).
  Resumed from `outputs/2026-11-10/02-20-57/resume_from_epoch80.ckpt` (copy of latest.ckpt) as job
  12316909 (`submit_paw_resume.sh`, same config + `++ckpt_path`). Dimer scan of the epoch-78 best: job 12316883.
- Archiving job 12316921 (`/depot/prism/data/rushik/archive_old_runs.sh`, log `archive_old_runs.log`):
  gzip of 14 old slurm logs + `zbl_updated/slurms/`; tar.gz of the W&B folders of the June/July runs,
  the failed 11-01 and cancelled 11-02/10-52 fine-tunes (their checkpoints/.hydra/train.log kept);
  gzip of superseded `cgst_train_dimers.xyz`, `cgst_train_clean.xyz`; tar.gz of
  `dft_atoms_dimers/dimers` and `dimers_nsp` (results.json, dimer xyz, npz, plots kept).
  Every original is removed only after its archive passes `pigz -t` (and `tar -t` for directories).
- Archiving job 12316921 finished in 5 min, 0 failures (log `rushik/archive_old_runs.log`); ~79 GB of
  originals → ~6.5 GB of verified archives.
- Dimer scan of the super_short scratch best so far (epoch 78, val F 0.138): every pair has a monotonic
  repulsive wall (no dips), DFT RMSE 0.11–0.19 eV per pair. Plots
  `CGST/dft_atoms_dimers/dimers_super_short_scratch_ep78_{full,binding}.png`. Early checkpoint — recheck at the end.

### 2026-11-13: resume failed (NaN) → fresh from-scratch restart
- Resume job 12316909 (2 GPUs, ++ckpt_path from epoch 80) went NaN at the start: best val = inf,
  30 non-finite weight tensors, lr decayed to 1e-5 by epoch 389. Cancelled. Second time 2-GPU (DDP)
  training broke right after loading a checkpoint (first: ModelFromCheckpoint fine-tune, job 12048329);
  2-GPU from-scratch runs have never failed this way.
- Restarted rushik_zbl_super_short from scratch with the unchanged `submit_paw.sh`/`config_paw.yaml`
  (2 GPUs, no checkpoint): job 12353289. Identical setup to the other four models.
- rushik_zbl_dataedge (12306555): epoch 465, best val F 0.1233, finite, lr 1e-3; ends ~2026-11-13 13:00.

## 15. Liquid/amorphous accuracy of the from-scratch models (2026-11-13, job 12356715)

`CGST/liquid_check/` (`liquid_check.py`, `analyze.py`, `liquid_check.csv`; ≤150 frames per type and split,
5125 frames). rushik_zbl_short, nequip_no_zbl, nequip_zbl all accurate on the DFT liquid, melt-quench and
amorphous frames, train and test alike: pressure bias −0.03 to −0.19 GPa (model slightly low), stress RMSE
0.10–0.21 GPa (shear 0.03–0.12), force RMSE 0.08–0.19 eV/Å. Disordered frames 4–7 meV/atom low relative to
crystal (slight over-stabilization). DFT melt-quench frames (5.82–5.84 g/cm³) sit at P_DFT ≈ −0.2 GPa and
the models agree, so on the data DFT and the models put the glass near 5.8–5.9 g/cm³. The 6.29 g/cm³ glass
(run-5 MD) therefore lies in structures absent from the training data; a ≤0.2 GPa bias alone moves density ~1 %.

## 16. Melt-quench with the from-scratch models (2026-11-13)

`zbl_updated/md_meltquench_scratch/<model>/`: same input and starting liquid as run 5's
`md_meltquench` (7200 atoms; 1500 K 50 ps → 10 K/ps to 300 K → 300 K 100 ps, 0 bar, 2 fs) with each
model's final best.ckpt (copied to model.ckpt, compiled in the job from the model's training folder).
In-run RDF dropped (g(r) from traj afterwards). 2× A30 each:
rushik_zbl_short 12356812, nequip_no_zbl 12356813, nequip_zbl 12356814, rushik_zbl_dataedge 12356815.
rushik_zbl_super_short (scratch) still waiting for A100s (12353289); its melt-quench follows when it finishes.

## 17. Amorphous density resolved (2026-11-14)

- From-scratch melt-quenches (section 16) all finished: glass 6.236–6.244 g/cm³ for rushik_zbl_short,
  nequip_no_zbl, nequip_zbl, rushik_zbl_dataedge (run 5: 6.286); crystal 6.239. Same local structure
  (Ge–Te 2.79–2.81 Å; CN Ge 4.41–4.43, Sb 3.78–3.82, Te 2.97–3.00), glass H ≈ crystal + 0.08 eV/atom.
- The DFT data already say this: GST_Melt_Quench frames binned by force RMS (proxy for T) — coldest
  48 frames (F_rms < 0.4 eV/Å): mean 6.258 g/cm³ (5.63–6.39) at P_DFT +0.04 GPa; hotter frames are
  less dense (0.4–0.6: 5.89; 0.6–0.8: 5.37). The earlier "~5.83 g/cm³" was the all-temperature average.
- `md_relax_dft_glass/` (job 12374487): 5 cold DFT melt-quench + 2 DFT amorphous frames held at 300 K,
  0 bar, 50 ps with nequip_zbl stay at 6.22–6.33 g/cm³ (mean ≈ 6.26). The model reproduces DFT here.
- Conclusion: amorphous ≈ crystal density is a property of the DFT reference (PBE + D2) / its training
  trajectories, not a model error. Versus experiment (a-GST ~5.9, c-GST ~6.27) the DFT level itself
  over-densifies the amorphous phase; fixing that needs a different reference, not retraining.
- Earlier claim retracted: Ge/Sb "diffusing at 300 K" in run 5 — the NPT MSD estimate is noise
  (−2.4 to +2.1 Å² across runs).

## 18. DFT single points on the model's own glass/liquid (2026-11-15)

Run on the CPU cluster, harvested with `CGST/dft_amorphous_check/pack_results.sh` →
`singlepoints.xyz` / `singlepoints.csv` (18/18 converged, 18–20 SCF steps).
- Controls reproduce their training labels exactly (ΔE_form < 0.1 meV, ΔP < 0.001 GPa) → setup = data.
- DFT static pressure on the run-5 300 K glass snapshots (6.28–6.31 g/cm³): 0.00, +0.28, −0.07 GPa →
  DFT is in equilibrium at the dense glass density. Confirms section 17: amorphous ≈ crystal density is the
  DFT reference's answer, not a model error.
- Model errors on these 15 unseen structures: from-scratch models dP −0.12 to −0.14 GPa, stress RMSE 0.14 GPa,
  force RMSE 0.115 eV/Å, dE −4 to −5 meV/atom; run 5 slightly worse (dP −0.25, 0.21, 0.124, −5.7).
  A −0.14 GPa bias corresponds to well under 1 % density.

## 19. External reference: GST-ACE-24 amorphous density (2026-11-15)

`CGST/GST-ACE-24/` (yace + training set + scripts provided). Runs with LAMMPS 2024-06-27 `pair_style pace`
from the shared fitsnap conda env (`/depot/amannodi/apps/bigconda/envs/fitsnap`); its liblammps needs
libjpeg.so.9, supplied by a private 1-MB env `GST-ACE-24/libjpeg9_env` on LD_LIBRARY_PATH (shared env untouched).
`submit_ace_mq.sh SEED RATE TAG [crystal]`: melt_quench.py (972 atoms, random start 5.5 g/cm³ → 3000 K NVT 10 ps →
1000 K NPT 50 ps → quench at RATE to 300 K → 300 K NPT 100 ps, density averaged over last 50 ps → 0 K box relax).
Jobs (10 K/ps, seeds 101/202/303): 12388617 (+ crystal.py), 12388618, 12388619. Results in `GST-ACE-24/results/`.
- Result: GST-ACE-24 with melt_quench.py does NOT give a glass. Seeds 101 and 202: once NPT starts (1000 K, 0 bar)
  the box expands without bound (5.5 → 0.001 g/cm³); the system breaks into ~150 clusters of 5–9 atoms
  (coordination 2–4) at −4.56 eV/atom, ~1 eV/atom BELOW ACE's own crystals (−3.40 to −3.54; DFT −3.49 to −3.63).
  ACE's dimers match our nsp DFT dimers within 0.02 eV and its isolated atoms are 0 eV, so both limits are right;
  the failure is overbinding of small low-coordination clusters. Seed 303 and the rest of 202 cancelled.
  The bundled script also reports density 0 (ave/time window never fires) and writes an empty RDF.
  Crystal check (crystal.py) fine: relaxed densities 5.86–6.22 g/cm³.
- Two follow-up ACE tests (2026-11-15):
  1. `GST-ACE-24/glass_relax/` (job 12388834): hold dense glasses at 300 K / 0 bar for 50 ps with ACE —
     the 7 DFT glass frames (144 atoms, 6.22–6.39 g/cm³) and the 7200-atom nequip_zbl glass (6.25 g/cm³).
  2. `GST-ACE-24/meltquench_ours/` (job 12388840): ACE through exactly our melt-quench (same 7200-atom 1500 K
     starting liquid, 1500 K NPT 50 ps → 10 K/ps → 300 K 100 ps); input = md_meltquench_scratch's with only
     pair_style pace and no Kokkos lines. 16 CPU cores, est. a few hours.
- glass_relax result (job 12388834): ACE puts our dense glasses (6.22–6.39 g/cm³) at +1.7 to +2.2 GPa (our
  PBE+D2 DFT: ~0), so within ~1 ps they expand to 5.4–5.5 g/cm³, then keep drifting down (5.5 → 5.0–5.3 over
  25 ps) with no stable plateau; 5 of 8 (incl. the 7200-atom glass at ~33 ps) then cavitate and break into
  clusters (PE −3.5 → −4.2…−4.46 eV/atom). 3 small cells still intact at 50 ps at 4.9–5.3 g/cm³.
  ACE cannot hold an amorphous solid at 300 K / 0 bar.
- meltquench_ours first attempt (12388840) failed in 17 s on my input error (dump_modify listed element C for a
  3-type system); fixed, resubmitted as 12393357.
- meltquench_ours result (job 12393357, 2 h 57 min, completed): with our exact protocol ACE also fails. The
  5.51 g/cm³ 1500 K liquid starts at +1.6 GPa under ACE and has broken up by 10 ps (0.74 g/cm³, PE −3.26 →
  −4.43 eV/atom); ends at 0.002 g/cm³, −4.59 eV/atom. No glass formed. Conclusion: GST-ACE-24 cannot be used
  for zero-pressure amorphous/liquid MD of GST (overbound small clusters), independent of protocol.

## 20. rushik_zbl_super_short (from scratch) follow-ups queued (2026-11-16)

Training job 12353289: epoch ~490, best val F 0.1220 (epoch 473), finite, lr 5e-4; ends ~13:10 today.
Queued with --dependency=afterok:12353289 so they use its final best.ckpt:
- 12398550 dimer + expansion scan → `CGST/dft_atoms_dimers/scan_super_short_final.npz` (`scan_job/scan_ss_final.py`)
- 12398551 melt-quench → `zbl_updated/md_meltquench_scratch/rushik_zbl_super_short/` (same input/start as the other
  four; submit_mq.sh copies best.ckpt to model.ckpt at job start, compiles from the rushik_zbl_super_short folder)

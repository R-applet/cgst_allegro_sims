# Validation results: nequip_zbl

Allegro with ZBL for every pair out to r_max, stock nequip 0.17.1 / allegro 0.8.2 (`models/provenance.md`, `training/configs/nequip_zbl/`). All jobs 2026-11-18 on perc A100-40GB (G, N) and alta
A100-80GB (K) with `--export=ALL,MODEL_ID=nequip_zbl,PMIX_MCA_gds=hash`. The machine-written verdicts are the `*.txt` files
next to this one (`INDEX.txt`: job and time of each); test labels and pass criteria: `../../RESULTS.md`.

**Verdict: the gate passes (RUNBOOK.md, B: model_check, smoke, dt, model_select); the 2 fs timestep is confirmed.**
The tests alongside (stress_parity, am_eos, density, glass_relax, compile_check, container, logic tests) have not run
for this model yet.

| Test | Result | nequip_no_zbl |
|---|---|---|
| 1b `model_check` (job 12430328, N) | compiled vs checkpoint: max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.2e-11 eV/Å, max \|ΔP\| 0.005 bar: PASS. Checkpoint vs DFT on the 13 frames: RMS 5.43 meV/atom, mean \|error\| 4.77, max 9.91 | RMS 5.4, mean 4.7, max 10.4 |
| `model_select` (12430329 G g000, 12430330 N n012, 12430331 K k028) | each node type picks its own file; G, N and K energies identical to 1b (max \|ΔE\| 0): PASS | PASS |
| 1a `smoke` (job 12431077, N) | x0 and x10 finish, no lost atoms, finite output: PASS | PASS |
| 1c `dt` (job 12431078, N) | NVE in the 1500 K x10 liquid, drift −0.0001 / −0.0003 / −0.0021 meV/atom/ps at 0.5 / 1 / 2 fs, all pass; at 2 fs drift margin 23.6×, std(E_tot)/std(PE) margin 1.6×: **2 fs** (`DT` in `common/model.sh`) | +0.0001 at 2 fs, margins 361× and 1.7× |

No A30 file has been compiled for this model, so it runs only on the A100 node types (G, N, K).

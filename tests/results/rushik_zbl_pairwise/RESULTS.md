# Validation results: rushik_zbl_pairwise

Allegro with per-pair ZBL at the edge of the training data (1.15–1.76 Å), Rushik's modified nequip 0.18.0 / allegro 0.8.3 (trained as rushik_zbl_dataedge) (`models/provenance.md`, `training/configs/rushik_zbl_pairwise/`). All jobs 2026-11-18 on perc A100-40GB (G, N) and alta
A100-80GB (K) with `--export=ALL,MODEL_ID=rushik_zbl_pairwise,PMIX_MCA_gds=hash`. The machine-written verdicts are the `*.txt` files
next to this one (`INDEX.txt`: job and time of each); test labels and pass criteria: `../../RESULTS.md`.

**Verdict: the gate passes (RUNBOOK.md, B: model_check, smoke, dt, model_select); the 2 fs timestep is confirmed; the
tests alongside (stress_parity, am_eos, density, glass_relax, compile_check, container) pass or agree with
nequip_no_zbl's: densities within 0.1%, held-out pressure RMSE 3–5% larger, EOS pressure RMSE about 20% larger.** Not run yet for this model: the logic tests (`mq_logic`, `recryst_logic`; code, not the
potential).

| Test | Result | nequip_no_zbl |
|---|---|---|
| 1b `model_check` (job 12430417, N) | compiled vs checkpoint: max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 2.3e-11 eV/Å, max \|ΔP\| 0.005 bar: PASS. Checkpoint vs DFT on the 13 frames: RMS 5.57 meV/atom, mean \|error\| 5.02, max 9.99 | RMS 5.4, mean 4.7, max 10.4 |
| `model_select` (12430418 G g003, 12430419 N n012, 12430420 K k011) | each node type picks its own file; G, N and K energies identical to 1b (max \|ΔE\| 0): PASS | PASS |
| 1a `smoke` (job 12430589, N) | x0 and x10 finish, no lost atoms, finite output: PASS | PASS |
| 1c `dt` (job 12430590, N) | NVE in the 1500 K x10 liquid, drift −0.0001 / −0.0002 / −0.0013 meV/atom/ps at 0.5 / 1 / 2 fs, all pass; at 2 fs drift margin 39.3×, std(E_tot)/std(PE) margin 1.6×: **2 fs** (`DT` in `common/model.sh`) | +0.0001 at 2 fs, margins 361× and 1.7× |
| `compile_check` (job 12434147, N) | a fresh recompile gives identical energies to the production N file (max \|ΔE\| 0; recompiled sha256 91c0614d…): PASS | PASS |
| 1f `container` (job 12434148, N) | stable vs debug image: identical energies; 3.13 vs 3.11 ns/day at 333 on 1 A100 (n-node) | PASS; 2.92 vs 2.91 ns/day (g-node) |
| 1h `stress_parity` (job 12434143) | 2403 held-out frames: pressure RMSE 1.74 kbar, mean bias −0.81 kbar, energy MAE 5.2 meV/atom | 1.65, −0.91, 4.8 |
| 1j `am_eos` (job 12434144) | 14 DFT EOS sets: mean \|Δρ0\| 0.47% (max 1.42%, C10 cubic), mean pressure RMSE 2.6 kbar | 0.42% (1.51%), 2.2 |
| 1g `density` (job 12434145, N) | x0 rocksalt 3×3×3 at 300 K, 0 bar: 30.449 Å³/atom, 6.224 g/cc | 30.451, 6.224 |
| 1i `glass_relax` (job 12434146, N) | DFT frames relaxed at 300 K, 0 bar: melt-quench glasses (5.86 g/cc) 6.233 (+6.7%); amorphous 6.244 (+1.0%); cubic 6.237 (+0.2%) | 6.222 (+6.5%), 6.234 (+0.8%), 6.238 (+0.3%) |
| 1k `dft_glass` (CPU, x0 r1 glass, `make_model_glass.py`, 2026-11-19) | **CONSISTENT**: model glass 6.237 g/cc vs DFT coldest-20 frames 6.235 (+0.02%), max \|ΔZ\| 0.11 (criterion 0.15) | CONSISTENT, +0.01%, 0.14 |

No A30 file has been compiled for this model, so it runs only on the A100 node types (G, N, K).

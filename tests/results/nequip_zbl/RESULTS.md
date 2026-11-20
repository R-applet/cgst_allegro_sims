# Validation results: nequip_zbl

Allegro with ZBL for every pair out to r_max, stock nequip 0.17.1 / allegro 0.8.2 (`models/provenance.md`, `training/configs/nequip_zbl/`). All jobs 2026-11-18 on perc A100-40GB (G, N) and alta
A100-80GB (K) with `--export=ALL,MODEL_ID=nequip_zbl,PMIX_MCA_gds=hash`. The machine-written verdicts are the `*.txt` files
next to this one (`INDEX.txt`: job and time of each); test labels and pass criteria: `../../RESULTS.md`.

**Verdict: the gate passes (RUNBOOK.md, B: model_check, smoke, dt, model_select); the 2 fs timestep is confirmed; the
tests alongside (stress_parity, am_eos, density, glass_relax, compile_check, container) pass or agree with
nequip_no_zbl's: densities within 0.1%, held-out pressure RMSE 3–5% larger, EOS pressure RMSE about 20% larger.** Not run yet for this model: the logic tests (`mq_logic`, `recryst_logic`; code, not the
potential).

| Test | Result | nequip_no_zbl |
|---|---|---|
| 1b `model_check` (job 12430328, N) | compiled vs checkpoint: max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.2e-11 eV/Å, max \|ΔP\| 0.005 bar: PASS. Checkpoint vs DFT on the 13 frames: RMS 5.43 meV/atom, mean \|error\| 4.77, max 9.91 | RMS 5.4, mean 4.7, max 10.4 |
| `model_select` (12430329 G g000, 12430330 N n012, 12430331 K k028) | each node type picks its own file; G, N and K energies identical to 1b (max \|ΔE\| 0): PASS | PASS |
| 1a `smoke` (job 12431077, N) | x0 and x10 finish, no lost atoms, finite output: PASS | PASS |
| 1c `dt` (job 12431078, N) | NVE in the 1500 K x10 liquid, drift −0.0001 / −0.0003 / −0.0021 meV/atom/ps at 0.5 / 1 / 2 fs, all pass; at 2 fs drift margin 23.6×, std(E_tot)/std(PE) margin 1.6×: **2 fs** (`DT` in `common/model.sh`) | +0.0001 at 2 fs, margins 361× and 1.7× |
| `compile_check` (job 12434140, N) | a fresh recompile gives identical energies to the production N file (max \|ΔE\| 0; recompiled sha256 8eb809c9…): PASS | PASS |
| 1f `container` (job 12434141, N) | stable vs debug image: identical energies; 3.13 vs 3.11 ns/day at 333 on 1 A100 (n-node) | PASS; 2.92 vs 2.91 ns/day (g-node) |
| 1h `stress_parity` (job 12434136) | 2403 held-out frames: pressure RMSE 1.70 kbar, mean bias −0.96 kbar, energy MAE 5.0 meV/atom | 1.65, −0.91, 4.8 |
| 1j `am_eos` (job 12434137) | 14 DFT EOS sets: mean \|Δρ0\| 0.46% (max 1.62%, C10 cubic), mean pressure RMSE 2.7 kbar | 0.42% (1.51%), 2.2 |
| 1g `density` (job 12434138, N) | x0 rocksalt 3×3×3 at 300 K, 0 bar: 30.428 Å³/atom, 6.229 g/cc | 30.451, 6.224 |
| 1i `glass_relax` (job 12434139, N) | DFT frames relaxed at 300 K, 0 bar: melt-quench glasses (5.86 g/cc) 6.209 (+6.2%); amorphous 6.239 (+0.9%); cubic 6.242 (+0.3%) | 6.222 (+6.5%), 6.234 (+0.8%), 6.238 (+0.3%) |
| 1k `dft_glass` (CPU, x0 r1 glass, `make_model_glass.py`, 2026-11-19) | **CONSISTENT**: model glass 6.234 g/cc vs DFT coldest-20 frames 6.235 (−0.02%), max \|ΔZ\| 0.12 (criterion 0.15) | CONSISTENT, +0.01%, 0.14 |

No A30 file has been compiled for this model, so it runs only on the A100 node types (G, N, K).

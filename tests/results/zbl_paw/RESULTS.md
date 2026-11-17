# Validation results: zbl_paw

Allegro with per-pair ZBL, PAW data, trained from scratch with Rushik's modified nequip 0.18.0 / allegro 0.8.3
(`models/provenance.md`). The machine-written verdicts are the `*.txt` files next to this one (`INDEX.txt`: job and
time of each, saved with `tests/collect.sh --save zbl_paw "2026-11-16 19:00"`); nozbl_paw's are in `../nozbl_paw/`.

**Verdict: short gate passed (2026-11-16).** By the user's choice, only `model_check` and `model_select` ran before
the phases study; smoke, dt and the rest of B (`RUNBOOK.md`) come before any melt-quench, and `DT` (0.002 ps) stays
provisional until `tests/dt` has run for this model.

| Test | Result | nozbl_paw |
|---|---|---|
| 1b `model_check` (job 12404521, g010, G file) | compiled vs checkpoint: max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 4.9e-11 eV/Å, max \|ΔP\| 0.005 bar: PASS. Checkpoint vs DFT on the 13 frames (144–768 atoms, 0–77 C): RMS 5.2 meV/atom, mean \|error\| 4.7, max 9.6 | RMS 5.4, mean 4.7, max 10.4 |
| `model_select` (12404522 G g010, 12404523 N n014, 12404524 K k050 on alta, 12404525 A30 b015 on strachan) | each node type picks its own file; G, N, K and A30 energies identical (max \|ΔE\| 0): PASS | PASS |

The first two `model_check` jobs (12403492 on g010, 12403592 on g008) died in `MPI_Init` with a PMIx segfault
before LAMMPS started, not a model failure; 12404521 was submitted with `--export=ALL,PMIX_MCA_gds=hash`
(`RUNBOOK.md`, cluster note). The checkpoint, saved by torch 2.12.1, loads and compiles in the container's torch 2.8
with version warnings only; `model_check`'s agreement at 1e-11 eV/Å confirms the compiled files reproduce it.

Not run yet: `smoke`, `dt`, `compile_check`, `container`, `stress_parity`, `am_eos`, `density`, `glass_relax`,
`dft_glass`, `mq_logic`, `recryst_logic`, `scaling`.

Physics check done outside `tests/`: the phases study (`phases/results/zbl_paw/RESULTS.md`), where zbl_paw reproduces
the DFT-MD RDF, ADF and VDOS of the 8 DFT cells as well as nozbl_paw.

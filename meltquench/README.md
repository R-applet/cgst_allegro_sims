# Melt-quench (`meltquench/`)

`in.meltquench` takes a 3×3×3 rocksalt cell (`structures/333/<cell>.data`) through melt and quench to an amorphous
sample at 300 K. Every stage is NPT, isotropic, 0 bar, with Nosé–Hoover damping Tdamp = 100 dt and Pdamp = 1000 dt.

This README describes the method; results are per model in `results/<MODEL_ID>/` (run5_ep301:
`results/run5_ep301/RESULTS.md` and its `report/`). Runs go to `runs/<MODEL_ID>/`; `MODEL_ID` is set in
`common/model.sh`, and the melt temperature, hold and quench rate come from `meltquench/params/<MODEL_ID>.sh`.

**Check the glass density for every model.** run5_ep301 quenches amorphous GST denser than its own rocksalt
(6.29 vs 6.24 g/cc), unlike experiment (glass ~6–7% less dense). It inherits this from its DFT reference
(`tests/RESULTS.md` 1g, 1k). Whether a retrained model does the same decides how densities, and anything that
depends on the glass–crystal density difference (crystallization strain, pressure-sensitive kinetics), can be
reported (`RUNBOOK.md`, B).

## Protocol

| Stage | T (K) | Duration | Purpose / output |
|---|---|---|---|
| 0 | minimize, then 300 | 20 ps | equilibrate the crystal |
| 1 | 300 → `tmelt` (1500 K default) | (tmelt − 300)/10 ps (10 K/ps) | apparent Tm from the enthalpy jump (superheated, an upper bound) |
| 2 | `tmelt` | `hold_ps` = 100 ps, the same for every run | **MSD gate**, checked 20 ps before the end: every species, C included, must have MSD ≥ 100 Å² within the hold (about 10 Å travelled). This erases memory of the crystal and of the C pattern repeated by the 3×3×3 replication. A run that fails stops with an ERROR before the quench; rerun *every* composition with a longer hold (`HOLD_PS`). Gate result → `gate.txt`. Liquid RDF over the last 20 ps → `rdf_<tmelt>K.dat`, `liquid_<tmelt>K.data` |
| 3 | `tmelt` → 300 | (tmelt − 300)/qrate ps, in 100 K segments | `snap_<T>K.data` every 100 K down to 300 K |
| 4 | 300 | 100 ps | 50 ps relaxation, then RDF and coordination averaged over 50 ps → `rdf_300K.dat`, `amorphous_300K.data` (input to recryst) |

**Why these choices**
- **Melt temperature `tmelt` (`TMELT` in params; 1500 K for run5_ep301).** Well above the model's superheated
  melting point, so the liquid is fast. For run5_ep301 the perfect crystal melts at about 1090 K when heated at 2 K/ps
  (reference run `md_npt_cubic_gst`; experiment ~900 K), and at 1500 K MSD grows at 7.5–9 Å²/ps for Ge/Sb/Te
  (reference `md_meltquench`: 380–450 Å² after 50 ps), so the gate is met well within 80 ps. For a new model, set it
  from that model's own superheating (`RUNBOOK.md`, meltquench). C diffusion is not known in advance, which is why the
  gate includes it.
- **A fixed hold, not one extended until the gate passes.** An adaptive hold would give a slow composition a
  longer melt than the others, and anything that evolves in the melt (C clustering, for one) would then differ
  between compositions for a reason that is not composition. So every run has the same hold, and the gate is a
  check that it was long enough.
- **10 K/ps quench.** This is the usual MLP/AIMD rate for GST and matches the reference run. The **1 K/ps
  sensitivity runs** (x0 and x10, one replica each) show how much the amorphous structure, density and Tg depend
  on rate. The 10 K/ps glasses already read `xfrac` ≈ 0.15 at 300 K, from persistent crystal-like patches
  (`recryst/README.md`, "Crystal-like order already in the glass"). A 1 K/ps glass well above that baseline, with a
  crystalline fraction that rises during the quench, means partial crystallization, which is itself a result for
  the C-free composition.
- **3 replicas per composition**, each with a different velocity seed, give error bars that cover sample-to-sample
  variation of the glass.

## On-the-fly output
| File | Interval | Contents |
|---|---|---|
| `mq.dat` | 1 ps | T, P, V/atom, ρ, PE/atom, H/atom, per-species MSD (from step 0), crystalline fraction (`common/in.analysis`) |
| `traj.lammpstrj.gz` | every 10 K on the ramps (1 ps heating; 10/qrate ps quench), 5 ps on the holds | id, type, x, y, z, per-atom q4 and crystal-like bond count |
| `rdf_<tmelt>K.dat`, `rdf_300K.dat` | one averaged block each | total g(r) and 10 partials with running coordination, 0–6 Å in 0.02 Å bins |
| `gate.txt` | once | `hold_ps`, the smallest per-species MSD in the hold, the gate it was compared with, and `passed` (0: the run stopped there with an ERROR in `log.mq`) |
| `mq.restart.a`, `.b` | every 50 ps, alternating | rolling restart files, for manual recovery only |
| `stages.txt` | once | actual heating and quench start and end times (ps). Each RDF window is preceded by up to one window of padding (`common/in.rdf`), so stages 2 and 4 can run up to 20 and 50 ps longer than the table above |

Coordination numbers use fixed bond cutoffs: 3.2 Å between Ge/Sb/Te (the common a-GST choice), 2.5 Å for C–Ge/Sb/Te
and 1.9 Å for C–C. Each C cutoff sits in the empty gap after its bonding peak. The first g(r) minimum is not used:
in the 10 K/ps glass, Te–Te has no bonding peak, and Ge–Te and Sb–Te tail off with no minimum before the second
shell, so first-minimum CNs come out at 6–11. Override with `--rc PAIR=R` (both analysis scripts).

Per-atom coordination is not dumped. One `coord/atom` cutoff cannot serve both bond families, so
`analysis/mq_structure.py` computes it from the dumped positions, with the same cutoff table.

## Running
```
cd meltquench
sbatch --array=0-14 submit.sh                         # QRATE from params (10 K/ps): 5 cells x 3 replicas
sbatch --array=0,12 --export=ALL,QRATE=1 submit.sh    # optional 1 K/ps sensitivity: x0 r1, x10 r1
# the same on one perc A100-40GB per run instead of 2 A30s (sbatch options override the #SBATCH lines):
sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --array=0-14 submit.sh
M=run5_ep301                                          # = MODEL_ID
python ../analysis/mq_summary.py --out results/$M runs/$M/*_q*_r*      # with env/cgst-ana active
python ../analysis/mq_structure.py --out results/$M runs/$M/*_q*_r*    # heavy: an sbatch job
```
Array index i → cell `(x0 x1 x2p5 x5 x10)[i/3]`, replica `i%3+1`; runs go to `runs/<MODEL_ID>/<cell>_q<qrate>_r<rep>/`.
strachan's 6-GPU A30 cap runs at most 3 of these jobs at once. One A100 gives 2.9–3.1 ns/day, close to the 3.35
ns/day of 2 A30s (`tests/RESULTS.md` 1d), so the perc queue roughly doubles throughput. `common/defaults.sh`
picks the right compiled model on either node type, and `submit.sh` passes `$SLURM_NTASKS` GPUs to LAMMPS.
Each run fits in one wall-time window: about 3–5 h at 10 K/ps and 11–13 h at 1 K/ps for 13.8k atoms on 2 A30s
(3.35 ns/day, `tests/RESULTS.md` 1d), against a 1-day limit. So a failed run is normally rerun from scratch. For
manual recovery, `snap_<T>K.data` marks each 100 K of the quench, and `mq.restart.a/b` hold the last two 50 ps
points of any stage. Resuming from them needs a hand-edited input that starts at the right stage.

`analysis/mq_summary.py` reports, per run and as replica mean ± sample std (NaN for a single replica):
- apparent Tm;
- liquid and amorphous density;
- Tg (bilinear V(T) fit on the quench);
- the crystalline fraction left at 300 K;
- the closest approach of any pair in the liquid and the glass (`rmin_l`, `rmin_a`, per pair below the table), with a
  WARNING below 1.0 Å (close contacts, a risk for potentials without ZBL; run5_ep301: C–C 1.10 Å in the x10 liquid,
  every other pair ≥ 1.64 Å);
- the hold length, with a WARNING if the runs do not all share one;
- partial coordination numbers (CN_ij, j atoms around an i atom) and each species' total coordination Z_i;
- with `--out`: `<group>_curves.dat`, ρ(T) and H(T) on the heating ramp and the quench, in 10 K bins.

`analysis/mq_structure.py` analyses the trajectory frames of the final 50 ps at 300 K and writes, per group, the
replica mean ± sample std of:
- `_zdist.dat`: the distribution of each species' total coordination Z;
- `_angles.dat`: the bond-angle distribution per centre species;
- `_sq.dat`: Faber–Ziman partial S_ij(q) and Bhatia–Thornton S_NN(q), from g(r) out to 15 Å with a Lorch window;
- `_cmotifs.dat`: each C atom's bonded-neighbour formula (e.g. Ge2Te1C1);
- `_cclusters.dat`: the fraction of C atoms in C–C clusters of each size.

## Validation
Both tests write a `RESULT.txt` with one PASS/FAIL line per check (`tests/collect.sh` prints them).

**`tests/mq_logic`: PASS** (job 12278869, with the `xfracGST` column). The full input runs on the 1×1×1 x0 (461 atoms) and x10 (512) cells with
every duration ×0.1, plus `x0_gatefail`: x0 with an unreachable gate (`gate_A2 1e9`). `check.py` runs at the end of
the job and verifies:
- every output file, including both restart files;
- 12 quench snapshots, and one RDF block per file;
- the four `stages.txt` times in order, with the temperature at each matching the schedule;
- `gate.txt` (`passed 1`) and exit status 0;
- that `mq_summary.py` and `mq_structure.py` run on the outputs, and that their two independent Z_i (RDF running
  coordination; bond counting on the trajectory) agree within 0.15 (measured: within 0.06);
- x0_gatefail: exit status non-zero, `passed 0`, the gate ERROR in `log.mq`, no quench, and the analysis scripts
  skip it naming the failed gate.

The 12 ps ramps on these small cells make Tm_app, Tg (NaN: under 20 quench points) and the structure numbers
meaningless; the test checks the logic only. With the uncalibrated default Q4 criterion, the glasses read
xfrac ≈ 0.1, the false-positive level the recryst calibration has to remove.

**`tests/mq_analysis`: PASS.** Independent checks of the analysis code:
- against Rushik's 10 K/ps reference glass (`md_meltquench`, 7200 atoms): partial g(r) matches his own g(r) from
  the same frames (peak shifts ≤ 0.11 Å, g → 1 at 14–15 Å); S_NN(q) peaks at 2.14 and 3.26 Å⁻¹, where amorphous
  GST's peaks sit; the Tg fit on its 121-point quench gives 675 K;
- known answers: on the perfect rocksalt lattice every Ge/Sb has Z = 6, the mean Z_Te equals
  6 (N_Ge + N_Sb)/N_Te exactly, and bond angles fall only at 90° and 180° (180° fraction 0.2); a toy C cell gives
  the exact cluster sizes, motifs and chain angle. Breaking the bond-vector sign in the angle code fails the toy
  cell check;
- replica statistics: the sample std (ddof 1) of 1, 2, 3 is 1, and a single value gives NaN;
- closest approach (`rmin_*`): on a synthetic RDF file, the first occupied bin per pair, NaN for an absent pair.

The reference data are frozen copies in `tests/mq_analysis/ref/` (sources and sha256s in `ref/SHA256SUMS`).

**`tests/dft_glass`: CONSISTENT for run5_ep301** (`tests/RESULTS.md` 1k; rerun per model with `MODEL_GLASS`). The model glass against DFT's own cold melt-quenched glass,
with the same code: density +0.85%, every mean Z within 0.08.

**Bugs this test has caught (all fixed):** the MSD-gate `min()`; first-minimum CNs (Te–Te ≈ 10, and Sb–Te ≈ 7 in
x10; now fixed cutoffs); repeated `mq.dat` rows breaking `np.gradient`; stage windows computed from the schedule
instead of `stages.txt`.

# Relaxed structures for DFT single points (run5_ep301 dense-glass check)

> **Status (2026-11-07): no longer needed to diagnose the model.** DFT's own cold melt-quenched glass in the
> training set is at 6.24 g/cc and zero pressure, with the same coordination as the model glass (`tests/RESULTS.md`
> 1k), so the dense glass comes from the DFT reference. The background below (1g–1i) predates that comparison and
> its "5.8 g/cc DFT glass" figure averaged hot frames. The single points would still be a direct check, if cheap.

**Request:** DFT single points (energy and stress, same settings as the CGST training data) on the structures in
`relaxed_for_dft.xyz`. They test whether run5_ep301's amorphous GST density (~6.28 g/cc) is real at the DFT level.

## Background (details in `tests/RESULTS.md`, 1g–1i)
- **1g.** The model's 10 K/ps melt-quench glass (7200 atoms) equilibrates at 6.287 g/cc at 300 K and 0 bar, which
  is *denser* than its rocksalt crystal (6.238). Experimentally the glass is about 6–7% less dense than the
  crystal.
- **1h.** On held-out DFT frames, the model's pressure is low by about 2 kbar (amorphous) and 1.6 kbar (cubic). That
  is only a few tenths of a percent in density, too small to explain the gap. DFT's own melt-quench glasses sit
  near 5.8 g/cc at about zero pressure.
- **1i.** Relaxing held-out DFT frames with the model (NPT, 300 K, 0 bar, 20 ps) takes the DFT melt-quench glasses
  from 5.86 to 6.27 g/cc (+7.3%). The crystal control moves only +0.8%.

## What is in `relaxed_for_dft.xyz`
36 structures of 144 atoms each (Ge/Sb/Te, no C): 12 each from `GST_Melt_Quench`, `AM_GST_runs` and `CUB_GST_runs`
of `cgst_test_paw.xyz`. Each is the final snapshot after 20 ps of model NPT at 300 K and 0 bar (dt 2 fs; model
compiled on an a100-40gb n-node, which gives energies identical to the production model).

Per-frame `info`:
- `source_frame`: the index of the starting frame in `cgst_test_paw.xyz`;
- `config_type`;
- `rho_dft_frame`: the starting density;
- `rho_model_300K`: the model density, averaged over the last 10 ps;
- `P_model_bar`: the model's mean pressure.

The cells are the LAMMPS-rotated cells of the original frames, isotropically rescaled by the barostat.

## How to read the answer
These are thermal snapshots at 300 K. DFT stress on them is the static virial, so the model's own static
prediction is the like-for-like comparison. At 0 bar total pressure, the static virial should be about −1.3 kbar
(minus the kinetic N k T / V at 300 K).
- **DFT virial far above that (several kbar or more, i.e. the cell wants to expand):** DFT does not support the
  dense glass. The model has a hole there, and these structures, or ones like them, belong in the training set.
- **DFT virial close to that:** DFT does support the dense glass, and the discrepancy with experiment lies in the
  DFT reference.

The crystal (`CUB_GST_runs`) structures are the control: they should come out near the DFT's own crystal value.

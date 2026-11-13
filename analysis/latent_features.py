"""Per-atom Allegro latent features, per-atom energies and Q4 crystal-like bond counts for LAMMPS dump frames.

For each selected frame, one forward pass of the eager checkpoint ($CKPT, from common/model.sh) yields:
  latent  (N, 256) float32  the invariant scalar edge features after the single Allegro layer (`edge_features`,
                            256x0e), mean-pooled over each atom's outgoing edges (edge_index[0] = centre atom)
  e_atom  (N,)              per-atom energy (`atomic_energy`, after per-type scale/shift and ZBL)
  ncb     (N,)              Q4 crystal-like bond count (analysis/bondorder.py; default criterion 3.6 A, 0.5)
plus types (LAMMPS 1-4 = Ge Sb Te C), step and box. The energy sum is checked against `total_energy`.

Must run inside the LAMMPS container with the modified nequip/allegro on PYTHONPATH (see tests/model_check/submit.sh):
  python latent_features.py out.npz DUMP[:step,step,...] [DUMP[:steps] ...] [--device cpu|cuda]
DUMP:steps restricts a dump to those timesteps; a bare DUMP takes every frame.
Output npz keys: per frame k, f<k>_latent, f<k>_e_atom, f<k>_ncb, f<k>_types, plus frames = "dump:step" labels.
"""
import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bondorder import crystal_bonds, read_dump  # noqa: E402

CKPT = os.environ.get("CKPT") or sys.exit("set CKPT (source common/model.sh): the model checkpoint to evaluate")
SYMBOLS = {1: "Ge", 2: "Sb", 3: "Te", 4: "C"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("dumps", nargs="+")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()

    warnings.filterwarnings("ignore")
    import torch
    from ase import Atoms
    from nequip.data import AtomicDataDict
    from nequip.integrations.ase import NequIPCalculator

    calc = NequIPCalculator._from_saved_model(CKPT, device=a.device)
    out, labels = {}, []
    for spec in a.dumps:
        path, _, steps = spec.partition(":")
        want = {int(s) for s in steps.split(",")} if steps else None
        for step, L, c in read_dump(path):
            if want is not None and step not in want:
                continue
            types = c["type"].astype(int)
            atoms = Atoms([SYMBOLS[t] for t in types], positions=c["pos"], cell=L, pbc=True)
            data = calc.atoms_to_data(atoms)
            res = calc.call_model(data)
            ei = res[AtomicDataDict.EDGE_INDEX_KEY][0].detach().cpu().numpy()
            feat = res[AtomicDataDict.EDGE_FEATURES_KEY].detach().cpu().numpy()
            e_atom = res[AtomicDataDict.PER_ATOM_ENERGY_KEY].detach().cpu().numpy().ravel()
            e_tot = float(res[AtomicDataDict.TOTAL_ENERGY_KEY].detach().cpu().numpy().ravel()[0])
            if not np.isclose(e_atom.sum(), e_tot, rtol=0, atol=1e-6 * len(types)):
                raise RuntimeError(f"{path}:{step}: sum(atomic_energy) {e_atom.sum()} != total_energy {e_tot}")
            n = len(types)
            cnt = np.bincount(ei, minlength=n)
            pooled = np.zeros((n, feat.shape[1]))
            np.add.at(pooled, ei, feat)
            pooled /= np.maximum(cnt, 1)[:, None]
            k = len(labels)
            out[f"f{k}_latent"] = pooled.astype(np.float32)
            out[f"f{k}_e_atom"] = e_atom
            out[f"f{k}_ncb"] = crystal_bonds(c["pos"], L, 3.6, 0.5)
            out[f"f{k}_types"] = types
            labels.append(f"{Path(path).name}:{step}")
            print(f"{labels[-1]}: {n} atoms, {feat.shape[0]} edges x {feat.shape[1]} features, "
                  f"E = {e_tot:.4f} eV", flush=True)
    np.savez_compressed(a.out, frames=np.array(labels), **out)


if __name__ == "__main__":
    main()

"""Structure renders for the Part 2 report (OVITO 3, Tachyon software renderer; no GPU or display needed).

From the last trajectory frame (300 K) of each melt-quench run:
  render_crystal_like  x0 glass, 10 K/ps vs 1 K/ps: a 12 A slab seen along z; crystal-like Ge/Sb/Te atoms (in-run
                       c_ncb >= 4, the Part 2 default criterion 3.6/0.5/4) in blue, other Ge/Sb/Te in light gray, C none
  render_c_network     x10 glass, 10 K/ps vs 1 K/ps: only the C atoms of the whole cell, with C-C bonds (1.9 A, the
                       runio.BOND_RC cutoff), seen along z
  render_c_network_all the same view for every C-containing composition (1-10% C), 10 K/ps, replica 1 (a 1x4 strip
                       for slides; render_c_network_all_grid, the same panels 2x2, for the printed report)
Writes meltquench/report/figures/<name>.png (panels composed with matplotlib, so titles match the other figures).
Colors from the dataviz reference palette: crystal-like = categorical slot 1 #2a78d6, C = slot 2 #eb6834, background
atoms = axis gray #c3c2b7.

Usage: env/cgst-ana/bin/python meltquench/report/render_structures.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ovito.io import import_file
from ovito.modifiers import (ComputePropertyModifier, CreateBondsModifier, DeleteSelectedModifier,
                             ExpressionSelectionModifier)
from ovito.vis import TachyonRenderer, Viewport

ROOT = Path(__file__).resolve().parents[4]
MODEL_ID = Path(__file__).resolve().parents[1].name   # this report lives in meltquench/results/<MODEL_ID>/report
RUNS, OUT = ROOT / "meltquench/runs" / MODEL_ID, Path(__file__).resolve().parent / "figures"
TMP = OUT / "_render_tmp"     # raw renders before paneling (removed at the end)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_figures as mf  # noqa: E402  (shared colors and rcParams)

BLUE, ORANGE, GRAY = (0x2a / 255, 0x78 / 255, 0xd6 / 255), (0xeb / 255, 0x68 / 255, 0x34 / 255), (0xc3 / 255,) * 3


def last_frame(run):
    p = import_file(str(RUNS / run / "traj.lammpstrj.gz"), columns=["Particle Identifier", "Particle Type",
                    "Position.X", "Position.Y", "Position.Z", "q4", "ncb"])
    return p, p.source.num_frames - 1


def render(pipeline, frame, path, size=(900, 900)):
    pipeline.add_to_scene()
    vp = Viewport(type=Viewport.Type.Top)
    vp.zoom_all(size)
    vp.render_image(size=size, filename=str(path), frame=frame, background=(0.988, 0.988, 0.984),
                    renderer=TachyonRenderer(ambient_occlusion=False, shadows=False))
    pipeline.remove_from_scene()


def crystal_like(run, path):
    p, f = last_frame(run)
    p.modifiers.append(ExpressionSelectionModifier(expression="ParticleType == 4 || Position.Z > 12"))
    p.modifiers.append(DeleteSelectedModifier())
    p.modifiers.append(ComputePropertyModifier(output_property="Color",
                       expressions=[f"ncb >= 4 ? {BLUE[0]} : {GRAY[0]}", f"ncb >= 4 ? {BLUE[1]} : {GRAY[1]}",
                                    f"ncb >= 4 ? {BLUE[2]} : {GRAY[2]}"]))
    p.modifiers.append(ComputePropertyModifier(output_property="Radius", expressions=["ncb >= 4 ? 1.1 : 0.8"]))
    data = p.compute(f)
    n = data.particles.count
    nx = int((data.particles["ncb"] >= 4).sum())
    render(p, f, path)
    return nx / n


def c_network(run, path):
    p, f = last_frame(run)
    p.modifiers.append(ExpressionSelectionModifier(expression="ParticleType != 4"))
    p.modifiers.append(DeleteSelectedModifier())
    p.modifiers.append(ComputePropertyModifier(output_property="Color",
                                               expressions=[str(ORANGE[0]), str(ORANGE[1]), str(ORANGE[2])]))
    p.modifiers.append(ComputePropertyModifier(output_property="Radius", expressions=["0.55"]))
    b = CreateBondsModifier(cutoff=1.9)
    b.vis.width = 0.35
    b.vis.use_particle_colors = True
    p.modifiers.append(b)
    data = p.compute(f)
    nb = data.particles.bonds.count if data.particles.bonds is not None else 0
    render(p, f, path)
    return data.particles.count, nb


def panel(pngs, titles, name, suptitle, grid=False):
    if grid:
        fig, axs = plt.subplots(2, 2, figsize=(9.2, 9.6)); axs = axs.ravel()
    else:
        fig, axs = plt.subplots(1, len(pngs), figsize=(4.6 * len(pngs), 4.9 if len(pngs) < 4 else 4.6))
    for ax, png, t in zip(axs, pngs, titles):
        ax.imshow(plt.imread(png)); ax.set_axis_off(); ax.set_title(t, fontsize=10)
    fig.suptitle(suptitle, x=0.02, ha="left", fontsize=11, fontweight="bold", color=mf.INK)
    fig.tight_layout()
    mf.save(fig, name)


if __name__ == "__main__":
    TMP.mkdir(parents=True, exist_ok=True)
    fr = {}
    for run in ("x0_q10_r1", "x0_q1_r1"):
        fr[run] = crystal_like(run, TMP / f"render_{run}.png")
    panel([TMP / "render_x0_q10_r1.png", TMP / "render_x0_q1_r1.png"],
          [f"quench 10 K/ps: {fr['x0_q10_r1']:.0%} crystal-like in slab", f"quench 1 K/ps: {fr['x0_q1_r1']:.0%} crystal-like in slab"],
          "render_crystal_like", "x0 (GST) glass at 300 K, 12 Å slab: crystal-like Ge/Sb/Te in blue")
    cn = {}
    for run in ("x10_q10_r1", "x10_q1_r1"):
        cn[run] = c_network(run, TMP / f"render_{run}.png")
    panel([TMP / "render_x10_q10_r1.png", TMP / "render_x10_q1_r1.png"],
          [f"quench 10 K/ps: {cn['x10_q10_r1'][0]} C, {cn['x10_q10_r1'][1]} C–C bonds",
           f"quench 1 K/ps: {cn['x10_q1_r1'][0]} C, {cn['x10_q1_r1'][1]} C–C bonds"],
          "render_c_network", "x10 glass at 300 K: C atoms only (whole cell), C–C bonds within 1.9 Å")
    LBL = {"x1": "1.07% C", "x2p5": "2.54% C", "x5": "5.14% C", "x10": "9.96% C"}
    cells = ["x1", "x2p5", "x5", "x10"]
    for c in cells:
        cn[c] = c_network(f"{c}_q10_r1", TMP / f"render_all_{c}.png")
    panel([TMP / f"render_all_{c}.png" for c in cells],
          [f"{LBL[c]}: {cn[c][0]} C, {cn[c][1]} C–C bonds" for c in cells],
          "render_c_network_all", "C atoms only (whole cell), C–C bonds within 1.9 Å; 10 K/ps glasses at 300 K")
    panel([TMP / f"render_all_{c}.png" for c in cells],
          [f"{LBL[c]}: {cn[c][0]} C, {cn[c][1]} C–C bonds" for c in cells],
          "render_c_network_all_grid", "C atoms only (whole cell), C–C bonds within 1.9 Å; 10 K/ps, 300 K", grid=True)
    for f in TMP.glob("*.png"):
        f.unlink()
    TMP.rmdir()

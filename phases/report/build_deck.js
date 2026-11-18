// Phases comparison slide deck -> phases_slides.pptx, from the figures of make_figures.py and the numbers in
// metrics_compare.txt / npt_compare.txt (the same content as phases_report.pdf). Structured deck (pptx skill): theme,
// two layouts, sections, placeholders, speaker notes; figure images for the curves, native tables for the numbers.
// Colors follow the figures (dataviz categorical slots 1-3). Image heights come from each PNG's own aspect ratio.
// Usage: NODE_PATH=<dir with node_modules/pptxgenjs> PPTX_SKILL=<pptx skill dir> node build_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(path.join(process.env.PPTX_SKILL, "scripts/apply_theme.js"));

const FIG = (n) => path.join(__dirname, "figures", n + ".png");
const ASPECT = (n) => { const b = fs.readFileSync(FIG(n)); return b.readUInt32BE(16) / b.readUInt32BE(20); };
const THEME = {
  name: "Allegro phases comparison", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "0B0B0B", lt1: "FFFFFF", dk2: "104281", lt2: "EEF3FA", accent1: "2A78D6", accent2: "EB6834",
            accent3: "1BAF7A", accent4: "5598E7", accent5: "86B6EF", accent6: "52514E", hlink: "2A78D6", folHlink: "1C5CAB" },
};
const HEX = { ink: "0B0B0B", ink2: "52514E", muted: "898781", grid: "E1E0D9", blue: "2A78D6", navy: "104281", orange: "EB6834", aqua: "1BAF7A", tint: "EEF3FA" };
const W = 13.333, H = 7.5, MX = 0.6, TOP = 1.35;

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "Three Allegro potentials against DFT-MD: the phases study";
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "DARK", background: { color: HEX.navy },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.3, w: W - 2 * MX, h: 1.6, fontSize: 38, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: MX, y: 4.05, w: W - 2 * MX, h: 2.8, fontSize: 18, color: C.background2, valign: "top" }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: "FFFFFF" },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: W - 2 * MX, h: 0.85, fontSize: 28, bold: true, color: C.text2, valign: "middle" }, text: "" } },
      { text: { text: "Phases study · nequip_no_zbl, nequip_zbl, rushik_zbl_pairwise vs DFT-MD", options: { x: MX, y: H - 0.42, w: 9, h: 0.3, fontSize: 10, color: HEX.muted } } },
    ],
    slideNumber: { x: W - MX - 0.6, y: H - 0.42, w: 0.6, h: 0.3, fontSize: 10, color: HEX.muted, align: "right" },
  });

  const content = (section, title) => {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const bullets = (s, items, opt) => s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
    { isTextBox: true, fontSize: 16, color: HEX.ink, paraSpaceAfter: 8, valign: "top", margin: 0, ...opt });
  const img = (s, name, x, y, w, objectName, hmax) => {
    const a = ASPECT(name);
    let ww = w, hh = w / a;
    if (hmax && hh > hmax) { hh = hmax; ww = hh * a; }
    s.addImage({ path: FIG(name), x, y, w: ww, h: hh, objectName, altText: objectName });
    return hh;
  };
  const tb = (t, o) => ({ text: t, options: { fontSize: 14, color: HEX.ink, ...o } });
  const th = (t) => tb(t, { bold: true, color: "FFFFFF", fill: { color: HEX.navy } });

  // 1. Title
  pres.addSection({ title: "Overview" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Overview" });
  s.addText("Three Allegro potentials against DFT-MD", { placeholder: "title" });
  s.addText("Structure, vibrations and density of the 8 DFT phase cells of Ge₂Sb₂Te₅ + C\nnequip_no_zbl · nequip_zbl · rushik_zbl_pairwise · November 2026", { placeholder: "body" });
  s.addNotes("Three Allegro potentials trained from scratch on the same PAW DFT data with identical settings, differing only in the short-range term: none (nequip_no_zbl), ZBL for every pair out to the 6 A cutoff (nequip_zbl), per-pair ZBL at the edge of the training data, 1.15-1.76 A (rushik_zbl_pairwise). Report: phases/report/phases_report.pdf.");

  // 2. Main message
  s = content("Overview", "At 300 K the three potentials are indistinguishable");
  const stats = [
    ["0.05–0.09", "RDF misfit R against DFT, every cell", "the three potentials within the seed scatter of each other"],
    ["0.87–0.95", "VDOS overlap with DFT", "same shared deviations: soft Ge/Sb/Te, stiff C at 10% C"],
    ["≤ 0.2%", "rocksalt vs glass density at 0 bar", "trigonal ~1.5% denser, for every potential"],
    ["< 2 SE", "the largest gap between potentials", "a-GST + 10% C: R 0.089 vs 0.071 / 0.075, same shape"],
  ];
  stats.forEach(([big, lab, sub], i) => {
    const x = MX + (i % 2) * 6.2, y = TOP + 0.15 + Math.floor(i / 2) * 2.75, w = 5.9, h = 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: HEX.tint }, line: { color: HEX.tint }, objectName: `stat card ${i + 1}` });
    s.addText(big, { isTextBox: true, x: x + 0.35, y: y + 0.25, w: w - 0.7, h: 1.0, fontSize: 40, bold: true, color: HEX.navy, fontFace: "Cambria", margin: 0 });
    s.addText(lab, { isTextBox: true, x: x + 0.35, y: y + 1.3, w: w - 0.7, h: 0.45, fontSize: 17, color: HEX.ink, margin: 0 });
    s.addText(sub, { isTextBox: true, x: x + 0.35, y: y + 1.78, w: w - 0.7, h: 0.45, fontSize: 13, color: HEX.ink2, margin: 0 });
  });
  s.addNotes("SE = standard error of the 3 seeds. The short-range term makes no measurable difference in these near-equilibrium 300 K cells; where it may matter, the hot liquid and close contacts, is the melt-quench comparison (running).");

  // 3. Method
  s = content("Overview", "Method: the DFT cells, the DFT protocol, three seeds");
  const steps = [["8 DFT cells", "144–160 atoms", "a-GST + 0/1.4/5.3/10% C; rocksalt, trigonal + 0/1.4% C"], ["NVT, DFT volume", "300 K, 1 fs", "5 ps + 20 ps every step"],
                 ["Analysis", "g(r), ADF, VDOS", "DoSPT; DFT's cutoffs"], ["NPT, 0 bar", "500 ps", "C-free cells: own density"]];
  const bw = 2.75, gap = (W - 2 * MX - 4 * bw) / 3;
  steps.forEach(([a, b, c], i) => {
    const x = MX + i * (bw + gap), y = TOP + 0.4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: 1.95, rectRadius: 0.12, fill: { color: HEX.tint }, line: { color: HEX.tint }, objectName: `step ${i + 1}` });
    s.addText([{ text: a, options: { bold: true, fontSize: 18, breakLine: true } }, { text: b, options: { fontSize: 14, breakLine: true } }, { text: c, options: { fontSize: 12 } }],
      { isTextBox: true, x: x + 0.15, y: y + 0.2, w: bw - 0.3, h: 1.6, color: HEX.ink, valign: "top", margin: 0 });
  });
  bullets(s, ["Same seeds for every potential; mean ± seed std unless stated",
              "R = RDF misfit over 1.5–6 Å (0 = DFT); overlaps = shared area of normalized curves (1 = DFT)",
              "Checks pass for all three: DoSPT vs exact velocities 1.0000, cell = box in all 36 runs, RDF/ADF code reproduces the DFT files",
              "Caveat: these DFT-MD cells are training data; one DFT trajectory per cell"], { x: MX, y: TOP + 2.75, w: W - 2 * MX, h: 2.6 });
  s.addNotes("Method details: phases/README.md. The amorphous cells were also analysed 20 ps later (_eq25): the glasses still relax (PE drift -7 to -15 meV/atom in the standard window, -0.3 to -7 later), but the metrics move by about the seed scatter or less.");

  // 4. Metrics summary
  pres.addSection({ title: "Structure" });
  s = content("Structure", "Every cell, every metric: the potentials overlap");
  img(s, "metrics_summary", MX, TOP + 0.05, W - 2 * MX, "metrics per cell for the three potentials", 4.6);
  s.addText("The cells differ more from each other than the potentials do. Small markers: seeds; large: mean of 3.", { isTextBox: true, x: MX, y: TOP + 4.8, w: W - 2 * MX, h: 0.4, fontSize: 14, color: HEX.ink2, margin: 0 });
  s.addNotes("Per cell: RDF misfit 0.046-0.089, ADF overlap 0.92-0.98, total VDOS overlap 0.87-0.95, total mean frequency within -6 to +6% of DFT. Table: phases_report.pdf, Table 1.");

  // 5. RDF
  s = content("Structure", "g(r): the three curves lie on top of each other");
  img(s, "rdf_all", MX, TOP + 0.05, W - 2 * MX, "total g(r) of the 8 cells", 4.75);
  s.addText("Crystals: first peak 3–11% taller than DFT's, for all three alike.", { isTextBox: true, x: MX, y: TOP + 4.85, w: W - 2 * MX, h: 0.4, fontSize: 14, color: HEX.ink2, margin: 0 });
  s.addNotes("Mean of 3 seeds per potential; DFT-MD dashed. RDF misfit per cell and potential: phases_report.pdf, Table 1.");

  // 6. ADF
  s = content("Structure", "Bond angles: octahedral-like, matched within 0.92–0.98");
  img(s, "adf_all", MX, TOP + 0.05, W - 2 * MX, "bond-angle distributions of the 8 cells", 4.75);
  s.addText("a-GST: all three find 19% fewer bond angles per atom than the DFT file (C-containing glasses within 3%).", { isTextBox: true, x: MX, y: TOP + 4.85, w: W - 2 * MX, h: 0.4, fontSize: 14, color: HEX.ink2, margin: 0 });
  s.addNotes("ADF with the DFT files' bond cutoffs; Sb-Te 3.2 or 3.4 A, matched per cell to the DFT file's angles per frame.");

  // 7. am_c10
  s = content("Structure", "a-GST + 10% C: the largest misfit, the same for all three");
  img(s, "am_c10_detail", MX, TOP + 0.05, W - 2 * MX, "am_c10 g(r) and difference from DFT", 3.9);
  bullets(s, ["R = 0.089 ± 0.006 (rushik_zbl_pairwise) vs 0.071 ± 0.008 and 0.075 ± 0.005 (SE of 3 seeds): under 2 SE",
              "Same deviation from DFT for every potential: taller C-bond peak at 2.0 Å (0.9 vs 0.65), second shell outward"],
          { x: MX, y: TOP + 4.1, w: W - 2 * MX, h: 1.3, fontSize: 15 });
  s.addNotes("The mean-of-seeds curves give R = 0.067, 0.070, 0.082: the gap comes from seed scatter, not from a different structure.");

  // 8. VDOS
  pres.addSection({ title: "Vibrations" });
  s = content("Vibrations", "VDOS: overlap 0.87–0.95, the same misses for all three");
  img(s, "vdos_all", MX, TOP + 0.05, W - 2 * MX, "total VDOS of the 8 cells", 4.75);
  s.addText("Trigonal GST: a sharp 2.9 THz peak where DFT has a broad 2.6–3.4 THz band (lowest overlap, 0.87–0.88).", { isTextBox: true, x: MX, y: TOP + 4.85, w: W - 2 * MX, h: 0.4, fontSize: 14, color: HEX.ink2, margin: 0 });
  s.addNotes("Each VDOS normalized over 0-60 THz and smoothed with the same 5-point boxcar as DFT's.");

  // 9. Per species
  s = content("Vibrations", "Ge/Sb/Te a little soft in the glasses, C stiff at 10% C");
  img(s, "nu_species", MX, TOP + 0.05, W - 2 * MX, "mean frequency per species vs DFT", 4.1);
  bullets(s, ["Amorphous: Ge, Sb, Te 1–10% below DFT (Sb at 10% C: 2.53–2.55 vs 2.79 THz); crystals within ~5%",
              "C at 10% C: 17.5–18.2 vs 15.1 THz (16–20% high), for all three"],
          { x: MX, y: TOP + 4.3, w: W - 2 * MX, h: 1.1, fontSize: 15 });
  s.addNotes("Error bars: seed std. rocksalt + 1.4% C has 2 C atoms: its C values scatter widely (nequip_zbl 13.0 +- 2.8 THz).");

  // 10. Carbon VDOS
  s = content("Vibrations", "Carbon: the right bands, individual peaks shifted");
  img(s, "c_vdos", MX, TOP + 0.1, W - 2 * MX, "VDOS of C in the C-containing cells", 3.6);
  bullets(s, ["C VDOS overlap with DFT 0.49–0.72, the least-matched quantity for every potential",
              "No potential is systematically closer to DFT for C"], { x: MX, y: TOP + 3.95, w: W - 2 * MX, h: 1.2, fontSize: 15 });
  s.addNotes("The cells hold 2-16 C atoms, so C spectra are noisy; per-cell numbers in metrics_compare.txt.");

  // 11. NPT
  pres.addSection({ title: "Density" });
  s = content("Density", "At 0 bar: rocksalt as dense as the glass, trigonal +1.5%");
  const h = img(s, "npt_density", MX, TOP + 0.05, 6.6, "density at 0 bar per phase and potential", 4.3);
  s.addTable([
    [th(""), th("glass"), th("rocksalt"), th("trigonal")],
    [tb("nequip_no_zbl"), tb("6.251 ± 0.013"), tb("6.241"), tb("6.343")],
    [tb("nequip_zbl"), tb("6.246 ± 0.016"), tb("6.248"), tb("6.342")],
    [tb("rushik_zbl_pairwise"), tb("6.232 ± 0.011"), tb("6.245"), tb("6.321")],
    [tb("DFT cell", { color: HEX.ink2 }), tb("6.193", { color: HEX.ink2 }), tb("6.311", { color: HEX.ink2 }), tb("6.412", { color: HEX.ink2 })],
  ], { x: MX + 6.8, y: TOP + 0.3, w: W - 2 * MX - 6.8, colW: [1.9, 1.5, 1.1, 1.03], rowH: 0.45, border: { type: "solid", pt: 0.75, color: HEX.grid }, valign: "middle", objectName: "density table" });
  bullets(s, ["g/cm³, 300 K, 0 bar; ± = SE of 3 seeds (crystal seeds agree to 0.0003)",
              "The DFT cells sit off the potentials' zero pressure: crystals expand ~1%, glass contracts",
              "Experiment: glass 6–7% lighter; the potentials follow their DFT reference"], { x: MX + 6.8, y: TOP + 3.0, w: W - 2 * MX - 6.8, h: 2.4, fontSize: 14 });
  s.addNotes("Crystal minus glass: rocksalt -0.15/+0.03/+0.20% (+-0.2%), trigonal +1.47/+1.55/+1.41%. The DFT reference's own melt-quenched glass is as dense as its crystal (tests/dft_glass).");

  // 12. Conclusions
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Density" });
  s.addText("Conclusions and next", { placeholder: "title" });
  s.addText([
    { text: "At 300 K the three potentials agree with each other within the seed scatter, and with DFT as closely", options: { bullet: true, breakLine: true } },
    { text: "Shared deviations (soft Ge/Sb/Te, stiff C, trigonal peak) come from the shared data and model, not the short-range term", options: { bullet: true, breakLine: true } },
    { text: "Next: the melt-quench comparison (hot liquid, close contacts), where the short-range term may matter", options: { bullet: true } },
  ], { placeholder: "body", paraSpaceAfter: 8 });
  s.addNotes("Melt-quench superheating pilots for nequip_zbl and rushik_zbl_pairwise are running (2026-11-18); replica-1 runs of every composition follow.");

  const out = path.join(__dirname, "phases_slides.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
}
main().catch((e) => { console.error(e); process.exit(1); });

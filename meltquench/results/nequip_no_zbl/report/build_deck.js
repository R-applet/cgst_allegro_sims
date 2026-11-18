// Melt-quench slide deck for this model -> meltquench_slides.pptx, from the figures of make_figures.py /
// render_structures.py and the numbers in meltquench/results/<MODEL_ID> (the same content as meltquench_report.pdf).
// Structured deck (pptx skill): theme, two layouts, sections, placeholders, speaker notes; native charts for the
// simple trends, figure images for curves, distributions and renders. Colors follow the figures (dataviz palette).
// Image heights come from each PNG's own aspect ratio, so regenerated figures keep their proportions.
// Usage: NODE_PATH=<dir with node_modules/pptxgenjs> PPTX_SKILL=<pptx skill dir> node build_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(path.join(process.env.PPTX_SKILL, "scripts/apply_theme.js"));

const MODEL_ID = path.basename(path.resolve(__dirname, ".."));
const FIG = (n) => path.join(__dirname, "figures", n + ".png");
const ASPECT = (n) => { const b = fs.readFileSync(FIG(n)); return b.readUInt32BE(16) / b.readUInt32BE(20); };
const THEME = {
  name: "GST carbon melt-quench", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "0B0B0B", lt1: "FFFFFF", dk2: "104281", lt2: "EEF3FA", accent1: "2A78D6", accent2: "EB6834",
            accent3: "1BAF7A", accent4: "5598E7", accent5: "86B6EF", accent6: "52514E", hlink: "2A78D6", folHlink: "1C5CAB" },
};
const HEX = { ink: "0B0B0B", ink2: "52514E", muted: "898781", grid: "E1E0D9", blue: "2A78D6", navy: "104281", orange: "EB6834", tint: "EEF3FA" };
const W = 13.333, H = 7.5, MX = 0.6, TOP = 1.35;

// Quench-rate results (x0 and x10, replica 1 at 5 and 1 K/ps; 10 K/ps: mean of 3), from mq_summary_rates.txt and
// mq_structure_q1.txt / mq_structure_q5.txt.
const RATE = {
  headline: "A 1 K/ps quench partially crystallizes the glass",
  bullets: [
    "Crystal-like Ge/Sb/Te at 300 K: 0.30 (0% C) and 0.21 (10% C) after 1 K/ps, vs 0.14 and 0.13 after 10 K/ps; 5 K/ps: 0.16 and 0.14",
    "It rises below ~650 K during the slow quench, and the 1 K/ps slab shows ordered domains: partly crystallized; C slows it",
    "Density does not change with rate (0% C: 6.239 g/cm³ at all three), and recrystallization starts from the 10 K/ps glasses",
  ],
  notes: "Single replicas at 5 and 1 K/ps; the 10 K/ps replica spread of xfracGST is up to 0.008, so the 5 K/ps rise (+0.015) is about two standard deviations, without ordered domains. At 1 K/ps the C network also coarsens (94% of C bonded to C, 89% in clusters of 10 or more, up to 223 atoms) and C bond angles turn planar (51% in 115-130 deg). Crystal-like = in-run Q4 bond count >= 4 (criterion 3.6/0.5/4).",
  stat: ["0.30", "crystal-like Ge/Sb/Te after a 1 K/ps quench (0% C)", "vs 0.14 at 10 K/ps: partial crystallization"],
};

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = `Melt-quench of Ge2Sb2Te5 + carbon with ${MODEL_ID}`;
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "DARK", background: { color: HEX.navy },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.3, w: W - 2 * MX, h: 1.6, fontSize: 40, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: MX, y: 4.05, w: W - 2 * MX, h: 2.6, fontSize: 18, color: C.background2, valign: "top" }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: "FFFFFF" },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: W - 2 * MX, h: 0.85, fontSize: 30, bold: true, color: C.text2, valign: "middle" }, text: "" } },
      { text: { text: `Melt-quench of GST + C · Allegro ${MODEL_ID} (no ZBL)`, options: { x: MX, y: H - 0.42, w: 8, h: 0.3, fontSize: 10, color: HEX.muted } } },
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
  // image of width w (or fitted into w x hmax), returns its height
  const img = (s, name, x, y, w, objectName, hmax) => {
    const a = ASPECT(name);
    let ww = w, hh = w / a;
    if (hmax && hh > hmax) { hh = hmax; ww = hh * a; }
    s.addImage({ path: FIG(name), x, y, w: ww, h: hh, objectName, altText: objectName });
    return hh;
  };
  const lineChart = (s, title, xs, series, fmt, opt) => s.addChart(pres.charts.LINE, series.map(([name, values]) => ({ name, labels: xs, values })), {
    showTitle: true, title, titleFontSize: 14, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    chartColors: [HEX.blue], lineSize: 2, lineDataSymbol: "circle", lineDataSymbolSize: 8,
    showValue: false, catAxisTitle: "C content (at.%)", showCatAxisTitle: true, catAxisTitleColor: HEX.ink2, catAxisTitleFontSize: 12,
    catAxisLabelColor: HEX.ink2, valAxisLabelColor: HEX.ink2, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLineColor: "C3C2B7", valAxisLineShow: false,
    valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" },
    showLegend: false, ...opt,
  });
  const XS = ["0", "1.07", "2.54", "5.14", "9.96"];
  const THIS = `${MODEL_ID} (4×4×4)`;

  // 1. Title
  pres.addSection({ title: "Overview" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Overview" });
  s.addText("Melt-quench of Ge₂Sb₂Te₅ + carbon", { placeholder: "title" });
  s.addText(`Amorphous structure from the no-ZBL Allegro potential ${MODEL_ID}\n19 glasses, 0–10 at.% C, 4×4×4 cells · November 2026`, { placeholder: "body" });
  s.addNotes(`Melt-quench glasses made with ${MODEL_ID} (Allegro without the ZBL short-range term), in 4x4x4 cells of 29.5k-32.8k atoms. Five compositions, 0 to 10 at.% C, three replicas each at 10 K/ps, plus one run at 5 and one at 1 K/ps for 0 and 10% C. It is the first of the three potentials to be melt-quenched; nequip_zbl and rushik_zbl_pairwise (with ZBL terms) follow with the same protocol. These glasses are the starting point of the recrystallization study.`);

  // 2. Four results
  s = content("Overview", "Four results");
  const stats = [
    ["≥ 1.08 Å", "closest approach in any liquid, without ZBL", "C–C; no pair of any kind below 1.0 Å"],
    ["−2.3%", "glass density from 0 to 10% C", "6.239 → 6.094 g/cm³; the liquid falls 1.5%"],
    ["87%", "of C atoms bonded to C at 10% C", "0.24 at 1% C; at 10% C, 53% in clusters of ≥ 10 atoms"],
    RATE.stat,
  ];
  stats.forEach(([big, lab, sub], i) => {
    const x = MX + (i % 2) * 6.2, y = TOP + 0.15 + Math.floor(i / 2) * 2.75, w = 5.9, h = 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: HEX.tint }, line: { color: HEX.tint }, objectName: `stat card ${i + 1}` });
    s.addText(big, { isTextBox: true, x: x + 0.35, y: y + 0.25, w: w - 0.7, h: 1.0, fontSize: 44, bold: true, color: i === 2 ? HEX.orange : HEX.navy, fontFace: "Cambria", margin: 0 });
    s.addText(lab, { isTextBox: true, x: x + 0.35, y: y + 1.3, w: w - 0.7, h: 0.45, fontSize: 18, color: HEX.ink, margin: 0 });
    s.addText(sub, { isTextBox: true, x: x + 0.35, y: y + 1.78, w: w - 0.7, h: 0.4, fontSize: 14, color: HEX.ink2, margin: 0 });
  });
  s.addNotes("C lowers the density and the apparent melting point and segregates into C clusters. The glass transition is not on this list: its replica scatter exceeds any composition effect.");

  // 3. Protocol
  s = content("Overview", "Protocol: from crystal to glass");
  const steps = [["Equilibrate", "300 K, 20 ps", "rocksalt cell"], ["Heat", "→ 1500 K", "120 ps at 10 K/ps"],
                 ["Melt", "1500 K, 100 ps", "MSD gate ≥ 100 Å²"], ["Quench", "→ 300 K", "10, 5 or 1 K/ps"], ["Glass", "300 K, 100 ps", "relax + average"]];
  const bw = 2.2, gap = (W - 2 * MX - 5 * bw) / 4;
  steps.forEach(([a, b, c], i) => {
    const x = MX + i * (bw + gap), y = TOP + 0.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: 1.8, rectRadius: 0.12, fill: { color: i === 3 ? HEX.navy : HEX.tint }, line: { color: i === 3 ? HEX.navy : HEX.tint }, objectName: `stage ${i + 1}` });
    s.addText([{ text: a, options: { bold: true, fontSize: 18, breakLine: true } }, { text: b, options: { fontSize: 14, breakLine: true } }, { text: c, options: { fontSize: 13 } }],
      { isTextBox: true, x: x + 0.15, y: y + 0.2, w: bw - 0.3, h: 1.4, color: i === 3 ? "FFFFFF" : HEX.ink, valign: "top", margin: 0 });
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.08, y: y + 0.7, w: gap - 0.16, h: 0.4, fill: { color: HEX.blue }, line: { color: HEX.blue }, objectName: `arrow ${i + 1}` });
  });
  bullets(s, ["NPT at 0 bar (isotropic), dt = 2 fs (energy conserved in the 1500 K liquid), 4×4×4 cells of 29.5k–32.8k atoms on 2 A100s",
              "19 runs: 3 replicas × 5 compositions at 10 K/ps, plus one run at 5 and one at 1 K/ps for 0 and 10% C; all passed the melt gate",
              "Compositions 0, 1.07, 2.54, 5.14, 9.96 at.% C, C on cation vacancies; 10% C fills every vacancy",
              "Fixed bond cutoffs: 3.2 Å Ge/Sb/Te, 2.5 Å C–Ge/Sb/Te, 1.9 Å C–C"], { x: MX, y: TOP + 2.75, w: W - 2 * MX, h: 2.8 });
  s.addNotes("1500 K was confirmed by a pilot: 361 K above the highest apparent melting point. The smallest per-species MSD in the hold was 349-651 A^2, against the 100 A^2 gate, so every species, C included, forgot the crystal and the repeated C pattern of the supercell.");

  // 4. No ZBL
  s = content("Overview", "No close contacts without ZBL");
  const tb = (t, o) => ({ text: t, options: { fontSize: 15, color: HEX.ink, ...o } });
  const th = (t) => tb(t, { bold: true, color: "FFFFFF", fill: { color: HEX.navy } });
  s.addTable([
    [th("Closest approach (Å), liquid 1500 K / glass 300 K"), th(MODEL_ID + ", all 10 K/ps runs")],
    [tb("Ge/Sb/Te pairs"), tb("≥ 1.98 / ≥ 2.24")],
    [tb("Ge–C"), tb("1.62–1.64 / 1.78–1.84")],
    [tb("Te–C"), tb("1.72–1.80 / 1.88–1.98")],
    [tb("C–C"), tb("1.08–1.12 / 1.16–1.20")],
  ], { x: MX, y: TOP + 0.2, w: W - 2 * MX, colW: [6.07, 6.06], rowH: 0.5, border: { type: "solid", pt: 0.75, color: HEX.grid }, valign: "middle", objectName: "closest approach table" });
  bullets(s, ["No pair below 1.0 Å; C–C just below the short end of real C–C bonds (1.2–1.5 Å) in the liquid, at it in the glass",
              "First comparison to make with the two ZBL potentials: do the closest approaches move?",
              "2 fs conserves energy in the 1500 K 10% C liquid (drift ≤ 0.0002 meV/atom/ps)"], { x: MX, y: TOP + 3.4, w: W - 2 * MX, h: 2.0 });
  s.addNotes("Without a short-range repulsive term only the training data keeps atoms apart at very short range, and the hot liquid is where that would fail first. Closest approach = first occupied 0.02 A bin of each partial RDF (liquid: last 20 ps of the 1500 K hold; glass: final 50 ps at 300 K). A brief contact could be missed by a time-averaged RDF; the timestep test would show it as drift or a crash, and it did not.");

  // 5. Density vs T
  pres.addSection({ title: "Thermodynamics" });
  s = content("Thermodynamics", "C lowers density in the liquid and the glass");
  let h = img(s, "density_vs_T", MX, TOP + 0.1, 8.0, "density vs temperature, heating and quench");
  bullets(s, ["Heating: the superheated crystal melts near 1100 K; earlier with more C",
              "Quench: density falls steadily with C at every temperature",
              "Glass at 300 K: 6.239 (0%) → 6.094 g/cm³ (10%)"], { x: MX + 8.35, y: TOP + 0.3, w: W - 2 * MX - 8.35, h: 3.6 });
  s.addText("Mean of 3 replicas per composition, 10 K/ps", { isTextBox: true, x: MX, y: TOP + 0.2 + h, w: 8, h: 0.35, fontSize: 11, color: HEX.muted, margin: 0 });
  s.addNotes("This model's 0% C glass (6.239) is as dense as its own rocksalt crystal (6.224 g/cm3), and as dense as the DFT reference's own cold glass (+0.01%). Experimentally the glass is 6-7% lighter than the crystal; that difference belongs to the DFT reference, not the fit.");

  // 6. Properties vs C (native charts)
  s = content("Thermodynamics", "C lowers the density and the apparent melting point");
  lineChart(s, "Glass density at 300 K (g/cm³)", XS, [[THIS, [6.239, 6.231, 6.213, 6.174, 6.094]]], "0.000",
            { x: MX, y: TOP + 0.1, w: 5.9, h: 4.3, valAxisMinVal: 6.05, valAxisMaxVal: 6.27, valAxisLabelFormatCode: "0.00" });
  lineChart(s, "Apparent melting point (K)", XS, [[THIS, [1139, 1138, 1112, 1069, 978]]], "0",
            { x: MX + 6.2, y: TOP + 0.1, w: 5.9, h: 4.3, valAxisMinVal: 900, valAxisMaxVal: 1200, valAxisLabelFormatCode: "0" });
  s.addText("Mean of 3 replicas (sample std: density ≤ 0.002 g/cm³; melting point ≤ 20 K). Density falls 2.3% (glass) and 1.5% (liquid) from 0 to 10% C; the melting point is flat to 1% C, then falls. Tg scatters by 5–22 K with no trend in C.",
            { isTextBox: true, x: MX, y: TOP + 4.6, w: W - 2 * MX, h: 0.8, fontSize: 14, color: HEX.ink2, margin: 0 });
  s.addNotes("Apparent melting point = fastest enthalpy rise on the 10 K/ps heating ramp; an upper bound on the model's Tm. Values per composition: meltquench/results/nequip_no_zbl/RESULTS.md.");

  // 7. Coordination
  pres.addSection({ title: "Structure" });
  s = content("Structure", "Coordination drops slightly with C");
  h = img(s, "coordination_vs_C", MX, TOP + 0.1, W - 2 * MX, "mean coordination per species against C");
  bullets(s, ["Ge 4.42 → 4.37, Sb 3.81 → 3.72, Te 2.99 → 2.84 from 0 to 10% C: a small, steady drop, as the glass gets lighter",
              "C itself: 3.76-coordinated at 1% C, 3.04 at 10%, as more of its neighbours are other C atoms"],
          { x: MX, y: TOP + 0.35 + h, w: W - 2 * MX, h: 1.6 });
  s.addNotes("Error bars: sample std over 3 replicas.");

  // 8. Angles and S(q)
  s = content("Structure", "Octahedral-like, a little more tetrahedral with C");
  h = img(s, "ge_angles", MX, TOP + 0.1, 5.95, "Ge bond-angle distribution per composition");
  img(s, "sq_nn", MX + 6.2, TOP + 0.1, 5.95, "S_NN(q) per composition", h);
  bullets(s, ["Ge bond angles peak at 91–93° for every composition; the 100–120° share rises 0.20 → 0.27",
              "S_NN(q) barely changes beyond 2 Å⁻¹"],
          { x: MX, y: TOP + 0.35 + h, w: W - 2 * MX, h: 1.5 });
  s.addNotes("Left: bond-angle distribution at Ge, normalized to unit area, 10 K/ps glasses. The 90 deg peak and the 165-170 deg shoulder are the octahedral-like (defective rocksalt) motif; the 100-120 deg share is the tetrahedral-like Ge fraction. Right: Bhatia-Thornton S_NN(q) from the partial g(r) out to 15 A with a Lorch window.");

  // 9. Carbon clustering
  pres.addSection({ title: "Carbon" });
  s = content("Carbon", "C segregates into C clusters");
  lineChart(s, "Fraction of C bonded to another C", ["1.07", "2.54", "5.14", "9.96"], [[THIS, [0.24, 0.51, 0.70, 0.87]]], "0.00",
            { x: MX, y: TOP + 0.1, w: 5.6, h: 4.1, chartColors: [HEX.orange], valAxisMinVal: 0, valAxisMaxVal: 1, valAxisLabelFormatCode: "0.0" });
  img(s, "render_c_network", MX + 5.85, TOP + 0.1, 6.25, "x10 glass, C atoms only, at each quench rate", 4.1);
  bullets(s, ["At 10% C, 53% of C sits in clusters of ≥ 10 atoms, the largest of 69",
              "C environments turn from Ge/Sb-rich (Ge₃Sb, Ge₂Sb₂) to C-rich (C₂, C₃, GeC₂); C binds Ge before Sb before Te"],
          { x: MX, y: TOP + 4.4, w: W - 2 * MX, h: 1.1 });
  s.addNotes("Right panel: C atoms of the whole 10% C cell, seen along z, after each quench rate. C neighbours per atom at 10% C: 0.44 per Ge, 0.18 per Sb, 0.04 per Te.");

  // 10. C network across compositions
  s = content("Carbon", "From scattered C atoms to a C network");
  h = img(s, "render_c_network_all", MX, TOP + 0.1, W - 2 * MX, "C atoms only, 1.07 to 9.96% C, 10 K/ps");
  bullets(s, ["C–C bonds per C atom (mean of 3 replicas): 0.26 (1.07% C), 0.67 (2.54%), 1.09 (5.14%), 1.63 (9.96%)",
              "Isolated C atoms and dimers at low C; short chains by 2.5%; branched clusters at 5–10%",
              "Whole 96.5 Å cell projected along z, so some apparent contacts are depth overlaps"],
          { x: MX, y: TOP + 0.4 + h, w: W - 2 * MX, h: 2.2 });
  s.addNotes("Replica 1 of each composition at 10 K/ps.");

  // 11. C bond angles
  s = content("Carbon", "C bonding: tetrahedral at low C, broader at 10%");
  img(s, "c_angles", MX, TOP + 0.1, 8.6, "C-centred bond-angle distributions");
  bullets(s, ["1.07% C: one peak at 109°, sp³-like (61% of angles in 100–115°)",
              "9.96% C: 44% in 115–130° (sp²-like), 39% in 100–115°: broad, between the two",
              "Matches C coordination falling 3.76 → 3.04"],
          { x: MX + 8.85, y: TOP + 0.2, w: W - 2 * MX - 8.85, h: 4.6, fontSize: 15 });
  s.addNotes("Angle shares are areas of the distribution in the given windows. Right panel: the 10% C glass at 10, 5 and 1 K/ps.");

  // 12. Quench rate
  pres.addSection({ title: "Quench rate" });
  s = content("Quench rate", RATE.headline);
  h = img(s, "quench_order", MX, TOP + 0.1, 6.4, "crystal-like order on cooling at 10, 5 and 1 K/ps");
  img(s, "render_crystal_like", MX + 6.6, TOP + 0.1, 5.5, "x0 glass slab, crystal-like atoms in blue, per quench rate", h);
  bullets(s, RATE.bullets, { x: MX, y: TOP + 0.3 + h, w: W - 2 * MX, h: 5.2 - h });
  s.addNotes(RATE.notes);

  // 13. Cutoff check
  s = content("Quench rate", "Bond cutoffs hold on this model's 10% C glasses");
  h = img(s, "c_cutoffs", MX, TOP + 0.1, W - 2 * MX, "partial g(r) for C pairs with cutoffs");
  bullets(s, ["g_CC(1.9 Å) = 0 in all four 10% C glasses (10 and 5 K/ps)",
              "At 2.5 Å, g is 0.05–0.07 (Ge–C) and 0.09–0.11 (Sb–C), on peak tails; ±0.1 Å moves C coordination by < 1% (Ge), < 3% (Sb)",
              "Cutoffs kept"], { x: MX, y: TOP + 0.4 + h, w: W - 2 * MX, h: 1.8 });
  s.addNotes("The C cutoffs (2.5 A for C-Ge/Sb/Te, 1.9 A for C-C) were checked on this model's glasses. Each sits in the gap after its bonding peak.");

  // 14. Summary, with the comparison still to come
  pres.addSection({ title: "Wrap-up" });
  s = content("Wrap-up", `${MODEL_ID}: summary, and the comparison still to come`);
  const pend = (t) => tb(t, { color: HEX.muted, italic: true });
  s.addTable([
    [th(""), th(MODEL_ID + " (no ZBL)"), th("nequip_zbl"), th("rushik_zbl_pairwise")],
    [tb("Glass density, 0 / 10% C (g/cm³)"), tb("6.239 / 6.094"), pend("to run"), pend("to run")],
    [tb("Glass vs own crystal"), tb("as dense (6.224)"), pend("to run"), pend("to run")],
    [tb("Apparent melting point, 0 / 10% C"), tb("1139 / 978 K"), pend("to run"), pend("to run")],
    [tb("C bonded to C at 10% C"), tb("0.87, largest cluster 69"), pend("to run"), pend("to run")],
    [tb("Closest C–C, liquid"), tb("1.08 Å"), pend("to run"), pend("to run")],
    [tb("vs DFT (pressure RMSE)"), tb("1.65 kbar"), pend("validation pending"), pend("validation pending")],
  ], { x: MX, y: TOP + 0.2, w: W - 2 * MX, colW: [3.9, 3.0, 2.6, 2.63], rowH: 0.55, border: { type: "solid", pt: 0.75, color: HEX.grid }, valign: "middle", objectName: "summary table" });
  s.addNotes("Pressure RMSE on 2403 held-out DFT frames (tests/stress_parity); everything else from the melt-quench runs. The other two potentials (ZBL for all pairs; per-pair ZBL at the data edge) are being compiled and validated, then melt-quenched with the same protocol.");

  // 15. Limitations and next steps
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Wrap-up" });
  s.addText("Limits, and what comes next", { placeholder: "title" });
  s.addText([
    { text: "Glass as dense as the crystal (experiment: 6–7% lighter), inherited from the DFT reference", options: { bullet: true, breakLine: true } },
    { text: "MD rates: Tm_app is a superheating limit; Tg depends on rate; one replica each at 5 and 1 K/ps", options: { bullet: true, breakLine: true } },
    { text: "One potential so far: nequip_zbl and rushik_zbl_pairwise get the same melt-quench next", options: { bullet: true, breakLine: true } },
    { text: "Recrystallization of these glasses: growth velocity against temperature per composition (x0 done, the rest in part)", options: { bullet: true } },
  ], { placeholder: "body", paraSpaceAfter: 8 });
  s.addNotes("The recrystallization study has its calibrated criterion (3.9 A / 0.6 / 4), the heating ramps and the x0 anneal grid (500-700 K); the other compositions are partly done.");

  const out = path.join(__dirname, "meltquench_slides.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
}
main().catch((e) => { console.error(e); process.exit(1); });

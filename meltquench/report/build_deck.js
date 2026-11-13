// Part 2 (melt-quench) slide deck -> part2_slides.pptx, from the figures of make_figures.py / render_structures.py
// and the numbers in meltquench/results (same content as part2_results.md and part2_report.pdf).
// Structured deck (pptx skill): theme, two layouts, sections, placeholders, speaker notes; native charts for the
// simple trends, figure images for curves, distributions and renders. Colors follow the figures (dataviz palette).
// Usage: NODE_PATH=<dir with node_modules/pptxgenjs> PPTX_SKILL=<pptx skill dir> node build_deck.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(path.join(process.env.PPTX_SKILL, "scripts/apply_theme.js"));

const FIG = (n) => path.join(__dirname, "figures", n + ".png");
const THEME = {
  name: "GST carbon melt-quench", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "0B0B0B", lt1: "FFFFFF", dk2: "104281", lt2: "EEF3FA", accent1: "2A78D6", accent2: "EB6834",
            accent3: "1C5CAB", accent4: "5598E7", accent5: "86B6EF", accent6: "52514E", hlink: "2A78D6", folHlink: "1C5CAB" },
};
const HEX = { ink: "0B0B0B", ink2: "52514E", muted: "898781", grid: "E1E0D9", blue: "2A78D6", navy: "104281", orange: "EB6834", tint: "EEF3FA" };
const W = 13.333, H = 7.5, MX = 0.6, TOP = 1.35;

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "Melt-quench of Ge2Sb2Te5 + carbon (Part 2 results)";
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
      { text: { text: "Part 2 · melt-quench of GST + C · Allegro run5_ep301", options: { x: MX, y: H - 0.42, w: 8, h: 0.3, fontSize: 10, color: HEX.muted } } },
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
  const img = (s, name, x, y, w, aspect, objectName) => s.addImage({ path: FIG(name), x, y, w, h: w / aspect, objectName, altText: objectName });
  const lineChart = (s, title, xs, ys, fmt, opt) => s.addChart(pres.charts.LINE, [{ name: title, labels: xs, values: ys }], {
    showTitle: true, title, titleFontSize: 14, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    chartColors: [HEX.blue], lineSize: 2, lineDataSymbol: "circle", lineDataSymbolSize: 8,
    showValue: true, dataLabelPosition: "t", dataLabelFormatCode: fmt, dataLabelColor: HEX.ink2, dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt",
    catAxisTitle: "C content (at.%)", showCatAxisTitle: true, catAxisTitleColor: HEX.ink2, catAxisTitleFontSize: 12,
    catAxisLabelColor: HEX.ink2, valAxisLabelColor: HEX.ink2, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLineColor: "C3C2B7", valAxisLineShow: false,
    valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" }, showLegend: false, ...opt,
  });
  const XS = ["0", "1.07", "2.54", "5.14", "9.96"];

  // 1. Title
  pres.addSection({ title: "Overview" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Overview" });
  s.addText("Melt-quench of Ge₂Sb₂Te₅ + carbon", { placeholder: "title" });
  s.addText("Amorphous structure from the Allegro potential run5_ep301\nPart 2 results · 17 glasses, 0–10 at.% C · November 2026", { placeholder: "body" });
  s.addNotes("Part 2 of the GST + C study: melt-quench glasses that the recrystallization work (Part 3) starts from. Five compositions, 0 to 10 at.% C, three replicas each at 10 K/ps plus one 1 K/ps run for 0 and 10% C.");

  // 2. Four results
  s = content("Overview", "Four results");
  const stats = [
    ["−2.2%", "glass density from 0 to 10% C", "6.289 → 6.148 g/cm³; liquid −1.4%"],
    ["1129 → 984 K", "apparent melting point, 0 → 10% C", "superheating limit at 10 K/ps"],
    ["91%", "of C atoms bonded to C at 10% C", "an extended C network, clusters up to 129 atoms"],
    ["2×", "crystal-like order after a 1 K/ps quench", "0.28 vs 0.155: partial crystallization"],
  ];
  stats.forEach(([big, lab, sub], i) => {
    const x = MX + (i % 2) * 6.2, y = TOP + 0.15 + Math.floor(i / 2) * 2.75, w = 5.9, h = 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: HEX.tint }, line: { color: HEX.tint }, objectName: `stat card ${i + 1}` });
    s.addText(big, { isTextBox: true, x: x + 0.35, y: y + 0.25, w: w - 0.7, h: 1.0, fontSize: 44, bold: true, color: i === 2 ? HEX.orange : HEX.navy, fontFace: "Cambria", margin: 0 });
    s.addText(lab, { isTextBox: true, x: x + 0.35, y: y + 1.3, w: w - 0.7, h: 0.45, fontSize: 18, color: HEX.ink, margin: 0 });
    s.addText(sub, { isTextBox: true, x: x + 0.35, y: y + 1.78, w: w - 0.7, h: 0.4, fontSize: 14, color: HEX.ink2, margin: 0 });
  });
  s.addNotes("Glass transition is not on this list on purpose: replica scatter (20-60 K) exceeds any composition effect.");

  // 3. Protocol
  s = content("Overview", "Protocol: from crystal to glass");
  const steps = [["Equilibrate", "300 K, 20 ps", "rocksalt cell"], ["Heat", "→ 1500 K", "120 ps at 10 K/ps"],
                 ["Melt", "1500 K, 100 ps", "MSD gate ≥ 100 Å²"], ["Quench", "→ 300 K", "10 K/ps or 1 K/ps"], ["Glass", "300 K, 100 ps", "relax + average"]];
  const bw = 2.2, gap = (W - 2 * MX - 5 * bw) / 4;
  steps.forEach(([a, b, c], i) => {
    const x = MX + i * (bw + gap), y = TOP + 0.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: 1.8, rectRadius: 0.12, fill: { color: i === 3 ? HEX.navy : HEX.tint }, line: { color: i === 3 ? HEX.navy : HEX.tint }, objectName: `stage ${i + 1}` });
    s.addText([{ text: a, options: { bold: true, fontSize: 18, breakLine: true } }, { text: b, options: { fontSize: 14, breakLine: true } }, { text: c, options: { fontSize: 13 } }],
      { isTextBox: true, x: x + 0.15, y: y + 0.2, w: bw - 0.3, h: 1.4, color: i === 3 ? "FFFFFF" : HEX.ink, valign: "top", margin: 0 });
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.08, y: y + 0.7, w: gap - 0.16, h: 0.4, fill: { color: HEX.blue }, line: { color: HEX.blue }, objectName: `arrow ${i + 1}` });
  });
  bullets(s, ["NPT at 0 bar (isotropic), dt = 2 fs, 3×3×3 cells of 12.4k–13.8k atoms",
              "17 runs: 3 replicas × 5 compositions at 10 K/ps, plus one 1 K/ps run for 0 and 10% C; all passed the melt gate",
              "Compositions 0, 1.07, 2.54, 5.14, 9.96 at.% C, C on cation vacancies; 10% C fills every vacancy",
              "Fixed bond cutoffs: 3.2 Å Ge/Sb/Te, 2.5 Å C–Ge/Sb/Te, 1.9 Å C–C"], { x: MX, y: TOP + 2.75, w: W - 2 * MX, h: 2.8 });
  s.addNotes("The melt gate checks that every species, C included, diffuses at least 10 Å during the 1500 K hold, erasing the crystal and the repeated C pattern of the 3x3x3 supercell.");

  // 4. Density vs T
  pres.addSection({ title: "Thermodynamics" });
  s = content("Thermodynamics", "C lowers density in the liquid and the glass");
  img(s, "density_vs_T", MX, TOP + 0.1, 8.0, 2.135, "density vs temperature, heating and quench");
  bullets(s, ["Heating: the superheated crystal melts near 1100 K; earlier with more C",
              "Quench: density falls steadily with C at every temperature",
              "Glass at 300 K: 6.289 (0%) → 6.148 g/cm³ (10%)"], { x: MX + 8.35, y: TOP + 0.3, w: W - 2 * MX - 8.35, h: 3.6 });
  s.addText("Mean of 3 replicas per composition, 10 K/ps", { isTextBox: true, x: MX, y: TOP + 0.2 + 8.0 / 2.135, w: 8, h: 0.35, fontSize: 11, color: HEX.muted, margin: 0 });
  s.addNotes("The model's glass is denser than its own crystal (6.29 vs 6.24), inherited from the DFT reference; crystallization therefore expands the cell here.");

  // 5. Properties vs C (native)
  s = content("Thermodynamics", "Density and melting point fall with C");
  lineChart(s, "Glass density at 300 K (g/cm³)", XS, [6.289, 6.277, 6.260, 6.221, 6.148], "0.000",
            { x: MX, y: TOP + 0.1, w: 5.9, h: 4.3, valAxisMinVal: 6.10, valAxisMaxVal: 6.32, valAxisLabelFormatCode: "0.00" });
  lineChart(s, "Apparent melting point (K)", XS, [1129, 1128, 1117, 1077, 984], "0",
            { x: MX + 6.2, y: TOP + 0.1, w: 5.9, h: 4.3, valAxisMinVal: 900, valAxisMaxVal: 1200, valAxisLabelFormatCode: "0" });
  s.addText("Mean of 3 replicas (sample std: density ≤ 0.004 g/cm³; melting point up to ±35 K at 10% C). Tg from a bilinear V(T) fit scatters by 20–60 K between replicas, more than any C effect.",
            { isTextBox: true, x: MX, y: TOP + 4.6, w: W - 2 * MX, h: 0.8, fontSize: 14, color: HEX.ink2, margin: 0 });
  s.addNotes("Apparent melting point = fastest enthalpy rise on the 10 K/ps heating ramp; an upper bound on the model's Tm.");

  // 6. Coordination
  pres.addSection({ title: "Structure" });
  s = content("Structure", "Coordination drops slightly with C");
  img(s, "coordination_vs_C", MX, TOP + 0.1, W - 2 * MX, 4.271, "mean coordination per species against C");
  bullets(s, ["Ge 4.49 → 4.43, Sb 3.86 → 3.80, Te 3.03 → 2.90 from 0 to 10% C",
              "C itself: 3.70-coordinated at 1% C, 3.02 at 10%, as more of its neighbours are other C atoms"],
          { x: MX, y: TOP + 0.35 + (W - 2 * MX) / 4.271, w: W - 2 * MX, h: 1.6 });
  s.addNotes("Error bars: sample std over 3 replicas.");

  // 7. Angles and S(q)
  s = content("Structure", "Octahedral-like, a little more tetrahedral with C");
  img(s, "ge_angles", MX, TOP + 0.1, 5.95, 1.786, "Ge bond-angle distribution per composition");
  img(s, "sq_nn", MX + 6.2, TOP + 0.1, 5.95 * 1.575 / 1.786 * 1.0, 1.575, "S_NN(q) per composition");
  bullets(s, ["Ge bond angles peak at 91–93° for every composition; the 100–120° share rises 0.19 → 0.25",
              "S_NN(q) barely changes beyond 2 Å⁻¹; the low-q rise at 10% C is consistent with a segregated C network"],
          { x: MX, y: TOP + 0.35 + 5.95 / 1.786, w: W - 2 * MX, h: 1.5 });
  s.addNotes("Left: bond-angle distribution at Ge, normalized to unit area, 10 K/ps glasses. The 90 deg peak and the 165-170 deg shoulder are the octahedral-like (defective rocksalt) motif; the 100-120 deg share is the tetrahedral-like Ge fraction. Right: Bhatia-Thornton S_NN(q) from the partial g(r) out to 15 A with a Lorch window. The low-q rise was not analysed further.");

  // 8. Carbon clustering (native + render)
  pres.addSection({ title: "Carbon" });
  s = content("Carbon", "C segregates into an extended network");
  lineChart(s, "Fraction of C bonded to another C", ["1.07", "2.54", "5.14", "9.96"], [0.30, 0.63, 0.80, 0.91], "0.00",
            { x: MX, y: TOP + 0.1, w: 5.6, h: 4.1, chartColors: [HEX.orange], valAxisMinVal: 0, valAxisMaxVal: 1, valAxisLabelFormatCode: "0.0" });
  img(s, "render_c_network", MX + 5.85, TOP + 0.1, 6.25, 1.858, "x10 glass, C atoms only, 10 and 1 K/ps");
  bullets(s, ["At 10% C, 75% of C sits in clusters of ≥ 10 atoms (up to 129)",
              "C environments turn from Ge/Sb-rich (Ge₃Sb) to C-rich (C₃, GeC₂); C binds Ge before Sb before Te"],
          { x: MX, y: TOP + 4.4, w: W - 2 * MX, h: 1.1 });
  s.addNotes("Right panel: C atoms of the whole 10% C cell, seen along z. After a 1 K/ps quench the network coarsens: 95% of C in clusters of 10 or more, up to 286.");

  // 8b. C network across compositions
  s = content("Carbon", "From scattered C atoms to a C network");
  img(s, "render_c_network_all", MX, TOP + 0.1, W - 2 * MX, 3.921, "C atoms only, 1.07 to 9.96% C, 10 K/ps");
  bullets(s, ["C–C bonds per C atom (mean of 3 replicas): 0.34 (1.07% C), 0.90 (2.54%), 1.35 (5.14%), 1.84 (9.96%)",
              "Isolated C atoms and dimers at low C; short chains by 2.5%; branched, connected clusters at 5–10%",
              "Whole 72 Å cell projected along z, so some apparent contacts are depth overlaps"],
          { x: MX, y: TOP + 0.4 + (W - 2 * MX) / 3.921, w: W - 2 * MX, h: 2.2 });
  s.addNotes("Replica 1 of each composition at 10 K/ps. Bond counts from the rendering (1.9 A C-C cutoff) agree with mq_summary's C-C coordination: 2 x 22 / 135 = 0.33 at 1.07% C, 2 x 454 / 675 = 1.35 at 5.14% C.");

  // 8c. C bond angles
  s = content("Carbon", "C bonding turns from tetrahedral toward planar");
  img(s, "c_angles", MX, TOP + 0.1, 8.6, 2.854, "C-centred bond-angle distributions");
  bullets(s, ["1.07% C: one peak at 109°, sp³-like (59% of angles in 100–115°)",
              "9.96% C: the main peak moves to 119°, sp²-like (48% in 115–130°), as C bonds to C",
              "Matches C coordination falling 3.70 → 3.02",
              "A 1 K/ps quench pushes further toward sp² (56% in 115–130°)"],
          { x: MX + 8.85, y: TOP + 0.2, w: W - 2 * MX - 8.85, h: 4.6, fontSize: 15 });
  s.addNotes("A small near-linear population (~170 deg) appears from 2.5% C at 10 K/ps and almost vanishes at 1 K/ps. Angle shares are areas of the distribution in the given windows.");

  // 9. Quench rate
  pres.addSection({ title: "Quench rate" });
  s = content("Quench rate", "A 1 K/ps quench partially crystallizes the glass");
  img(s, "quench_order", MX, TOP + 0.1, 6.4, 2.319, "crystal-like order on cooling, 10 vs 1 K/ps");
  img(s, "render_crystal_like", MX + 6.6, TOP + 0.1, 5.5, 1.858, "x0 glass slab, crystal-like atoms in blue, 10 vs 1 K/ps");
  bullets(s, ["Crystal-like Ge/Sb/Te at 300 K: 0.28 (0% C) and 0.26 (10% C) after 1 K/ps, vs 0.13–0.16 after 10 K/ps",
              "It rises between 600 and 400 K during the slow quench: partly crystallized, not just better relaxed",
              "So the recrystallization study (Part 3) starts from the 10 K/ps glasses"],
          { x: MX, y: TOP + 3.25, w: W - 2 * MX, h: 2.0 });
  s.addNotes("Glass density barely depends on rate (0% C: 6.283 vs 6.289 g/cm3). Crystal-like = in-run Q4 bond count >= 4 (criterion 3.6/0.5/4).");

  // 10. Cutoff check
  s = content("Quench rate", "Bond cutoffs hold on the production 10% C glass");
  img(s, "c_cutoffs", MX, TOP + 0.1, W - 2 * MX, 3.528, "partial g(r) for C pairs with cutoffs");
  bullets(s, ["g_CC(1.9 Å) = 0 in all four 10% C glasses",
              "At 2.5 Å, g is 0.05–0.09 for Ge–C and Sb–C, on peak tails; ±0.1 Å moves C coordination by ≤ 2% (Ge), 4–6% (Sb)",
              "Cutoffs kept"], { x: MX, y: TOP + 0.4 + (W - 2 * MX) / 3.528, w: W - 2 * MX, h: 1.8 });
  s.addNotes("The C cutoffs (2.5 A for C-Ge/Sb/Te, 1.9 A for C-C) were set on a small 12 ps logic-test glass and re-checked here on the three 10 K/ps and the 1 K/ps 10% C production glasses. Each sits in the gap after its bonding peak; the first g(r) minimum is not used because Te-Te has no bonding peak in this glass.");

  // 11. Limitations and next steps
  pres.addSection({ title: "Wrap-up" });
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Wrap-up" });
  s.addText("Limits, and what comes next", { placeholder: "title" });
  s.addText([
    { text: "Dense glass: the model's glass (6.29 g/cm³) is denser than its crystal (6.24), from its DFT reference", options: { bullet: true, breakLine: true } },
    { text: "MD rates: Tm_app is a superheating limit; Tg depends on rate", options: { bullet: true, breakLine: true } },
    { text: "Next (Part 3): isothermal anneals of the 10 K/ps glasses, growth velocity against temperature per composition", options: { bullet: true } },
  ], { placeholder: "body", paraSpaceAfter: 8 });
  s.addNotes("Dense glass: experimental amorphous GST is about 6-7% less dense than the cubic crystal; this model's glass is slightly denser than its own crystal, inherited from its DFT training reference, so density-dependent conclusions belong to that reference. Part 3 measures growth velocity against annealing temperature from homogeneous recrystallization of the 10 K/ps glasses, with seeded slabs for the temperatures where nuclei do not form.");

  const out = path.join(__dirname, "part2_slides.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
}
main().catch((e) => { console.error(e); process.exit(1); });

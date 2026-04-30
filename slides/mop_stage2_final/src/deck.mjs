import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import {
  Presentation,
  PresentationFile,
  column,
  grid,
  image,
  rule,
  text,
  fill,
  hug,
  fixed,
  fr,
  drawSlideToCtx,
} from "@oai/artifact-tool";

const require = createRequire(import.meta.url);
const artifactRoot = path.resolve(path.dirname(require.resolve("@oai/artifact-tool")), "..");
const skiaCanvasPath = path.join(artifactRoot, "node_modules/skia-canvas/lib/index.js");
const { Canvas } = await import(pathToFileURL(skiaCanvasPath).href);

const COLORS = {
  yellow: "#ffb000",
  orange: "#fe6100",
  pink: "#dc267f",
  purple: "#785ef0",
  blue: "#648fff",
  black: "#000000",
  white: "#ffffff",
  lightgrey: "#d9d9d9",
};

const FIGURE_ROOT =
  "/Users/barry/Library/Mobile Documents/com~apple~CloudDocs/Carnegie Mellon/15740/Proj/Mixture-of-Prefetchers/report/figures";

const deck = Presentation.create({ slideSize: { width: 1920, height: 1080 } });

function pngDataUrl(filename) {
  const data = fs.readFileSync(`${FIGURE_ROOT}/${filename}`).toString("base64");
  return `data:image/png;base64,${data}`;
}

function title(textValue, subtitle) {
  return column(
    { name: "title-stack", width: fill, height: hug, gap: 12 },
    [
      text(textValue, {
        name: "slide-title",
        width: fill,
        height: hug,
        style: { fontSize: 54, bold: true, color: COLORS.black },
      }),
      subtitle
        ? text(subtitle, {
            name: "slide-subtitle",
            width: fill,
            height: hug,
            style: { fontSize: 24, color: COLORS.black },
          })
        : rule({ name: "title-rule", width: fixed(240), stroke: COLORS.pink, weight: 5 }),
    ],
  );
}

function bulletList(items, fontSize = 28) {
  return column(
    { name: "bullet-list", width: fill, height: hug, gap: 16 },
    items.map((item, index) =>
      text(item, {
        name: `bullet-${index}`,
        width: fill,
        height: hug,
        style: { fontSize, color: COLORS.black },
      }),
    ),
  );
}

function addSlide(content) {
  const slide = deck.slides.add();
  slide.compose(content, {
    frame: { left: 0, top: 0, width: 1920, height: 1080 },
    baseUnit: 8,
  });
  return slide;
}

addSlide(
  grid(
    {
      name: "cover",
      width: fill,
      height: fill,
      columns: [fr(1.15), fr(0.85)],
      rows: [fr(1), fixed(120)],
      columnGap: 56,
      rowGap: 32,
      padding: { x: 96, y: 84 },
    },
    [
      column(
        { name: "cover-copy", width: fill, height: fill, gap: 28 },
        [
          text("Mixture-of-Prefetchers", {
            name: "cover-title",
            width: fill,
            height: hug,
            style: { fontSize: 76, bold: true, color: COLORS.black },
          }),
          rule({ name: "cover-rule", width: fixed(360), stroke: COLORS.pink, weight: 8 }),
          text("A small L2C router that closes the train-window pair-best gap and clears no-prefetch on heldout", {
            name: "cover-thesis",
            width: fill,
            height: hug,
            style: { fontSize: 34, color: COLORS.black },
          }),
        ],
      ),
      column(
        { name: "cover-metrics", width: fill, height: fill, gap: 36 },
        [
          text("0.9829x", {
            name: "cover-metric-1",
            width: fill,
            height: hug,
            style: { fontSize: 78, bold: true, color: COLORS.pink },
          }),
          text("train-window vs pair-best", {
            name: "cover-label-1",
            width: fill,
            height: hug,
            style: { fontSize: 26, color: COLORS.black },
          }),
          text("1.0033x", {
            name: "cover-metric-2",
            width: fill,
            height: hug,
            style: { fontSize: 78, bold: true, color: COLORS.blue },
          }),
          text("heldout vs no-prefetch", {
            name: "cover-label-2",
            width: fill,
            height: hug,
            style: { fontSize: 26, color: COLORS.black },
          }),
        ],
      ),
      text("CMU 15-740 class project, Stage 2 OpenEvolve report", {
        name: "cover-footer",
        columnSpan: 2,
        width: fill,
        height: hug,
        style: { fontSize: 22, color: COLORS.black },
      }),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 92, y: 70 }, gap: 34 },
    [
      title("What we added to Athena", "Athena is the simulator substrate. Our work is the router, sandboxed search, ledgers, and report pipeline."),
      grid(
        { name: "build-grid", width: fill, height: fill, columns: [fr(1), fr(1), fr(1)], columnGap: 48 },
        [
          bulletList(["Athena substrate", "ChampSim-derived simulator", "Existing L2C prefetchers", "AthenaMAB comparator"], 27),
          bulletList(["Our MoP layer", "Router aliases V0 through V1.3", "Epoch action logging", "Budget and sticky controls"], 27),
          bulletList(["Our evidence layer", "Frozen train/heldout split", "OpenEvolve candidate ledger", "Parser-preserving report assets"], 27),
        ],
      ),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 92, y: 70 }, gap: 34 },
    [
      title("Protocol: pair-best first, no-prefetch second"),
      grid(
        { name: "protocol-grid", width: fill, height: fill, columns: [fr(0.9), fr(1.1)], columnGap: 56 },
        [
          bulletList(["Expert pair: MLOP + SPP+PPF", "Cache level: L2C", "17 train traces", "7 heldout traces", "Heldout used after selection freeze"], 29),
          bulletList(["Primary comparator: pair-best single", "Secondary comparator: no-prefetch", "Practical floor: weaker expert", "Simple coordinators: WinnerTakeAll, OneShotFit, AthenaMAB"], 29),
        ],
      ),
      text("Selection used train/search surfaces. Heldout appears only after the seed is fixed.", {
        name: "protocol-footer",
        width: fill,
        height: hug,
        style: { fontSize: 22, color: COLORS.black },
      }),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 70, y: 56 }, gap: 18 },
    [
      title("OpenEvolve improved the train-window router", "MoP-V1.3 improves both train-window comparators, then shows a smaller heldout lift."),
      image({
        name: "pre-post-figure",
        dataUrl: pngDataUrl("stage2_pre_post_geomean.png"),
        contentType: "image/png",
        width: fill,
        height: fill,
        fit: "contain",
        alt: "Pre and post OpenEvolve geomean bars",
      }),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 70, y: 56 }, gap: 18 },
    [
      title("Heldout shows a modest geomean lift", "Heldout clears no-prefetch by geomean, while trace-level placement shows why pair-best remains the upper bar."),
      image({
        name: "heldout-profile",
        dataUrl: pngDataUrl("stage2_heldout_trace_profile.png"),
        contentType: "image/png",
        width: fill,
        height: fill,
        fit: "contain",
        alt: "Heldout trace profile with experts and router",
      }),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 70, y: 56 }, gap: 18 },
    [
      title("Model sweeps improved screens, confirmation kept the seed", "Scaled search found similar cheap-screen candidates, then 10-trace confirmation preserved the active seed at 0.9801x."),
      image({
        name: "scale-models",
        dataUrl: pngDataUrl("stage2_scale_model_comparison.png"),
        contentType: "image/png",
        width: fill,
        height: fill,
        fit: "contain",
        alt: "Scaled model search and confirmation comparison",
      }),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 92, y: 70 }, gap: 34 },
    [
      title("The evaluator made search auditable", "Candidate programs were allowed to change only a literal policy dictionary."),
      grid(
        { name: "audit-grid", width: fill, height: fill, columns: [fr(1), fr(1)], columnGap: 60 },
        [
          bulletList(["Allowed outputs", "Router choice", "Budget split knobs", "Sticky margin", "Score weights"], 29),
          bulletList(["Recorded failures", "Simulator SIGBUS rows", "Unknown policy keys", "Helper/import code", "Missing evolve markers"], 29),
        ],
      ),
      text("Ledger: 290 candidates, 225 valid scored rows, 65 fail-closed rows. Malformed or crashed candidates receive combined_score = -10.0.", {
        name: "audit-footer",
        width: fill,
        height: hug,
        style: { fontSize: 22, color: COLORS.black },
      }),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 92, y: 70 }, gap: 34 },
    [
      title("Defensible claims"),
      bulletList(
        [
          "Primary defended claim: Stage 2 closes the train-window gap against pair-best single.",
          "Heldout claim: the selected router clears no-prefetch in geomean.",
          "The selected router beats simple coordination baselines on the 13-trace train-window surface.",
          "Pair-best single remains the upper comparator, which keeps the claim honest.",
          "The final artifacts preserve raw metric paths, ledgers, configs, and generated figures.",
        ],
        31,
      ),
    ],
  ),
);

const pptx = await PresentationFile.exportPptx(deck);
await pptx.save("output/output.pptx");

for (const [index, slide] of deck.slides.items.entries()) {
  const canvas = new Canvas(1920, 1080);
  const ctx = canvas.getContext("2d");
  await drawSlideToCtx(slide, deck, ctx);
  await canvas.toFile(`scratch/slide-${String(index + 1).padStart(2, "0")}.png`);
}

console.log("slides", deck.slides.items.length);

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
          text("A small L2-cache router that improves IPC over disabled prefetching and tracks a max-prefetcher cap", {
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
          text("1.066x", {
            name: "cover-metric-1",
            width: fill,
            height: hug,
            style: { fontSize: 78, bold: true, color: COLORS.pink },
          }),
          text("13-trace training-split validation vs disabled prefetching", {
            name: "cover-label-1",
            width: fill,
            height: hug,
            style: { fontSize: 26, color: COLORS.black },
          }),
          text("1.003x", {
            name: "cover-metric-2",
            width: fill,
            height: hug,
            style: { fontSize: 78, bold: true, color: COLORS.blue },
          }),
          text("7-trace heldout vs disabled prefetching", {
            name: "cover-label-2",
            width: fill,
            height: hug,
            style: { fontSize: 26, color: COLORS.black },
          }),
        ],
      ),
      text("CMU 15-740 class project, OpenEvolve training-split report", {
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
          bulletList(["Our router layer", "MoP-V1 manual router", "MoP-V2 OpenEvolve-tuned router", "Epoch counters and budget controls"], 27),
          bulletList(["Our evidence layer", "17 train traces, 7 heldout traces", "OpenEvolve candidate ledger", "Generated tables and figures"], 27),
        ],
      ),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 92, y: 70 }, gap: 34 },
    [
      title("Protocol: disabled prefetching is 1x"),
      grid(
        { name: "protocol-grid", width: fill, height: fill, columns: [fr(0.9), fr(1.1)], columnGap: 56 },
        [
          bulletList(["Expert pair: MLOP + SPP+PPF", "Cache level: L2C", "Search: 10 training traces", "Training-split validation: 13 local traces", "Heldout: 7 traces after policy selection"], 29),
          bulletList(["Performance baseline: disabled prefetching", "Max-prefetcher cap: max(MLOP, SPP+PPF) per trace", "Minimum check: beat the worse prefetcher", "Simple routers: WinnerTakeAll, OneShotFit, AthenaMAB"], 29),
        ],
      ),
      text("The 13-trace training-split surface has complete local artifacts. The four other train traces are facesim, ligra_BFS, ligra_Triangle, and secret_compute_int_243.", {
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
      title("OpenEvolve improved the router", "Bars use disabled prefetching as 1x. Yellow caps show the per-trace max prefetcher."),
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
      title("Heldout shows a modest geomean lift", "Horizontal bars compare MLOP, SPP+PPF, and MoP-V2 on each heldout trace."),
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
      title("OpenEvolve search trajectory", "Left: 3-trace quick evaluation. Right: 10-trace wider validation. Lines show best-so-far by weighted score."),
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
      title("The evaluator made search auditable", "Candidate programs changed a literal policy dictionary."),
      grid(
        { name: "audit-grid", width: fill, height: fill, columns: [fr(1), fr(1)], columnGap: 60 },
        [
          bulletList(["Allowed outputs", "Router choice", "Budget split knobs", "Close-score tie margin", "Score weights"], 29),
          bulletList(["Recorded failures", "Simulator failures", "Unknown policy keys", "Helper/import code", "Missing evolve markers"], 29),
        ],
      ),
      text("Ledger: 374 candidates, 306 valid scored rows, 68 fail-closed rows. Malformed or crashed candidates receive combined_score = -10.0.", {
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
      title("Result scope"),
      bulletList(
        [
          "Primary claim: OpenEvolve improves IPC speedup over disabled prefetching on 13 training-split validation traces.",
          "Heldout claim: the selected router reaches 1.003x over disabled prefetching on seven heldout traces.",
          "Instruction-count ratios round to 1.000x on training-split validation and heldout.",
          "The max-prefetcher result remains a cap, which keeps the claim sized correctly.",
          "Reproduction paths and naming details live in report/writing_logistics.md.",
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

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
  auto,
  drawSlideToCtx,
} from "@oai/artifact-tool";

const require = createRequire(import.meta.url);
const artifactRoot = path.resolve(path.dirname(require.resolve("@oai/artifact-tool")), "..");
const skiaCanvasPath = path.join(artifactRoot, "node_modules/skia-canvas/lib/index.js");
const { Canvas } = await import(pathToFileURL(skiaCanvasPath).href);

const COLORS = {
  orange: "#fe6100",
  pink: "#dc267f",
  purple: "#785ef0",
  blue: "#648fff",
  darkblue: "#3f6fd1",
  black: "#000000",
  white: "#ffffff",
  lightgrey: "#d9d9d9",
};

const FIGURE_ROOT =
  "/Users/barry/Library/Mobile Documents/com~apple~CloudDocs/Carnegie Mellon/15740/Proj/Mixture-of-Prefetchers/report/figures";
const ASSET_ROOT =
  "/Users/barry/Library/Mobile Documents/com~apple~CloudDocs/Carnegie Mellon/15740/Proj/Mixture-of-Prefetchers/report/assets/material_symbols";

const deck = Presentation.create({ slideSize: { width: 1920, height: 1080 } });

function pngDataUrl(filename) {
  const data = fs.readFileSync(`${FIGURE_ROOT}/${filename}`).toString("base64");
  return `data:image/png;base64,${data}`;
}

function iconDataUrl(filename) {
  const data = fs.readFileSync(`${ASSET_ROOT}/${filename}.png`).toString("base64");
  return `data:image/png;base64,${data}`;
}

function title(textValue, subtitle) {
  return column(
    { name: "title-stack", width: fill, height: hug, gap: 10 },
    [
      text(textValue, {
        name: "slide-title",
        width: fill,
        height: hug,
        style: { fontSize: 50, bold: true, color: COLORS.black },
      }),
      subtitle
        ? text(subtitle, {
            name: "slide-subtitle",
            width: fill,
            height: hug,
            style: { fontSize: 23, color: "#333333" },
          })
        : rule({ name: "title-rule", width: fixed(240), stroke: COLORS.pink, weight: 5 }),
    ],
  );
}

function bulletList(items, fontSize = 27) {
  return column(
    { name: "bullet-list", width: fill, height: hug, gap: 14 },
    items.map((item, index) =>
      text(item, {
        name: `bullet-${index}`,
        width: fill,
        height: hug,
        style: { fontSize, color: COLORS.black, lineHeight: 1.15 },
      }),
    ),
  );
}

function eyebrow(value, color = COLORS.pink) {
  return text(value.toUpperCase(), {
    name: "eyebrow",
    width: fill,
    height: hug,
    style: { fontSize: 18, bold: true, color },
  });
}

function metric(value, label, color = COLORS.pink, valueSize = 66) {
  return column(
    { name: `metric-${label}`, width: fill, height: hug, gap: 8 },
    [
      text(value, {
        name: "metric-value",
        width: fill,
        height: hug,
        style: { fontSize: valueSize, bold: true, color },
      }),
      text(label, {
        name: "metric-label",
        width: fill,
        height: hug,
        style: { fontSize: 20, color: COLORS.black, lineHeight: 1.1 },
      }),
    ],
  );
}

function iconLead(icon, heading, body, color = COLORS.darkblue) {
  return grid(
    {
      name: `icon-lead-${heading}`,
      width: fill,
      height: hug,
      columns: [fixed(54), fr(1)],
      columnGap: 18,
    },
    [
      image({
        name: `icon-${icon}`,
        dataUrl: iconDataUrl(icon),
        contentType: "image/png",
        width: fixed(48),
        height: fixed(48),
        fit: "contain",
        alt: `${heading} icon`,
      }),
      column(
        { name: `icon-copy-${heading}`, width: fill, height: hug, gap: 5 },
        [
          text(heading, {
            name: `icon-heading-${heading}`,
            width: fill,
            height: hug,
            style: { fontSize: 26, bold: true, color, lineHeight: 1.05 },
          }),
          text(body, {
            name: `icon-body-${heading}`,
            width: fill,
            height: hug,
            style: { fontSize: 20, color: "#333333", lineHeight: 1.12 },
          }),
        ],
      ),
    ],
  );
}

function figureCaption(value) {
  return text(value, {
    name: "figure-caption",
    width: fill,
    height: hug,
    style: { fontSize: 19, color: "#333333", lineHeight: 1.12 },
  });
}

function keyValueRows(rows, columns = [fr(0.72), fr(1.28)], fontSize = 23) {
  return column(
    { name: "kv-rows", width: fill, height: hug, gap: 10 },
    rows.map(([key, value], index) =>
      grid(
        {
          name: `kv-row-${index}`,
          width: fill,
          height: hug,
          columns,
          columnGap: 22,
        },
        [
          text(key, {
            name: `kv-key-${index}`,
            width: fill,
            height: hug,
            style: { fontSize, bold: true, color: COLORS.black, lineHeight: 1.12 },
          }),
          text(value, {
            name: `kv-value-${index}`,
            width: fill,
            height: hug,
            style: { fontSize, color: "#333333", lineHeight: 1.12 },
          }),
        ],
      ),
    ),
  );
}

function resultTable(rows, widths, fontSize = 22) {
  return column(
    { name: "result-table", width: fill, height: hug, gap: 8 },
    rows.map((cells, rowIndex) =>
      grid(
        {
          name: `table-row-${rowIndex}`,
          width: fill,
          height: hug,
          columns: widths,
          columnGap: 18,
        },
        cells.map((cell, cellIndex) =>
          text(cell, {
            name: `table-cell-${rowIndex}-${cellIndex}`,
            width: fill,
            height: hug,
            style: {
              fontSize,
              bold: rowIndex === 0 || cellIndex === 0,
              color: rowIndex === 0 ? COLORS.darkblue : COLORS.black,
              lineHeight: 1.1,
            },
          }),
        ),
      ),
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
      columns: [fr(1), fr(1)],
      rows: [fr(1), fixed(86)],
      columnGap: 70,
      rowGap: 24,
      padding: { x: 92, y: 70 },
    },
    [
      column(
        { name: "cover-copy", width: fill, height: fill, gap: 26 },
        [
          eyebrow("OpenEvolve-tuned L2 cache prefetch routing", COLORS.darkblue),
          text("Mixture of Prefetchers", {
            name: "cover-title",
            width: fill,
            height: hug,
            style: { fontSize: 76, bold: true, color: COLORS.black, lineHeight: 0.96 },
          }),
          rule({ name: "cover-rule", width: fixed(460), stroke: COLORS.pink, weight: 8 }),
          text("A compact router chooses between MLOP and SPP+PPF after each epoch, then OpenEvolve tunes the policy dictionary.", {
            name: "cover-thesis",
            width: fill,
            height: hug,
            style: { fontSize: 31, color: COLORS.black, lineHeight: 1.12 },
          }),
          text("Final claim size: strong 13-trace training-split validation result, modest heldout generalization over disabled prefetching.", {
            name: "cover-scope",
            width: fill,
            height: hug,
            style: { fontSize: 25, color: "#333333", lineHeight: 1.15 },
          }),
        ],
      ),
      column(
        { name: "cover-purpose", width: fill, height: fill, gap: 30 },
        [
          iconLead("route", "Route the next epoch", "Use recent usefulness counters to choose MLOP, SPP+PPF, both, or the off action.", COLORS.darkblue),
          iconLead("tune", "Tune a small policy", "OpenEvolve changes budget, score weights, accuracy floor, and tie margin.", COLORS.pink),
          iconLead("fact_check", "Claim the right result size", "MoP-V2 reaches 1.066x on 13 training-split validation traces and 1.003x on heldout.", COLORS.orange),
        ],
      ),
      text("CMU 15-740 class project. Disabled prefetching is the 1.000x reference throughout.", {
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
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(0.95), fr(1.05)],
      rows: [auto, fr(1)],
      columnGap: 58,
      rowGap: 34,
      padding: { x: 92, y: 70 },
    },
    [
      title("What we built on Athena", "The project adds a router layer and a small policy-search loop above existing Athena L2C prefetchers."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "system-left", width: fill, height: fill, gap: 22 },
        [
          eyebrow("router names", COLORS.pink),
          keyValueRows(
            [
              ["MoP-V1", "Manual one-epoch probe router. It probes both experts, then routes to the higher-scoring expert."],
              ["MoP-V2", "OpenEvolve-tuned router. It keeps the same public role and tunes budget, scoring, and tie behavior."],
              ["Experts", "MLOP and SPP+PPF are the two Athena L2-cache prefetchers used by this router."],
            ],
            [fr(0.34), fr(1.66)],
            25,
          ),
        ],
      ),
      column(
        { name: "system-right", width: fill, height: fill, gap: 22 },
        [
          eyebrow("evidence layer", COLORS.darkblue),
          bulletList(
            [
              "Epoch-level counters record issued and useful prefetches.",
              "OpenEvolve edits a small literal policy dictionary.",
              "Generated candidate records preserve valid scored rows and fail-closed rows.",
              "Report tables and figures rebuild from simulator summaries.",
            ],
            28,
          ),
        ],
      ),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(1.05), fr(0.95)],
      rows: [auto, fr(1)],
      columnGap: 60,
      rowGap: 34,
      padding: { x: 92, y: 70 },
    },
    [
      title("Trace protocol and comparators", "All performance numbers use disabled prefetching as 1.000x. Best expert is a per-trace reference."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "protocol-left", width: fill, height: fill, gap: 20 },
        [
          eyebrow("fixed setup", COLORS.darkblue),
          keyValueRows(
            [
              ["Cache", "Athena L2C"],
              ["Expert pair", "MLOP + SPP+PPF"],
              ["Official split", "24 traces total: 17 training, 7 heldout"],
              ["Final validation", "13 available training traces, 500K warmup, 1M simulation"],
              ["Heldout", "7 frozen traces, 20M warmup, 50M simulation"],
              ["Epoch", "500K retired instructions"],
            ],
            [fr(0.54), fr(1.46)],
            23,
          ),
        ],
      ),
      column(
        { name: "protocol-right", width: fill, height: fill, gap: 20 },
        [
          eyebrow("comparison ladder", COLORS.pink),
          keyValueRows(
            [
              ["Disabled", "Universal 1.000x baseline."],
              ["Best expert", "max(MLOP, SPP+PPF) per trace, then geomeaned. It is colored dark blue in the result plots."],
              ["Worse expert", "Minimum practical check for whether routing clears the weaker constituent prefetcher."],
              ["Simple routers", "WinnerTakeAll, OneShotFit, and Athena MAB appear as small baselines."],
            ],
            [fr(0.48), fr(1.52)],
            24,
          ),
        ],
      ),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(0.8), fr(1.2)],
      rows: [auto, fr(1)],
      columnGap: 58,
      rowGap: 26,
      padding: { x: 76, y: 58 },
    },
    [
      title("OpenEvolve changed a small policy dictionary", "The search could tune router settings and numeric policy weights while the trace split and simulator stayed fixed."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "policy-copy", width: fill, height: fill, gap: 18 },
        [
          eyebrow("selected MoP-V2 policy", COLORS.pink),
          keyValueRows(
            [
              ["Budget", "9,216 prefetches per 500K-instruction epoch, about 18.4 per 1K retired instructions"],
              ["Probe", "One initial dual-expert probe epoch"],
              ["Guardrails", "Accuracy floor 30 and 3% close-score tie margin"],
              ["Weights", "Accuracy 1.0, coverage 0.55, traffic 1.0"],
            ],
            [fr(0.43), fr(1.57)],
            23,
          ),
        ],
      ),
      column(
        { name: "policy-score", width: fill, height: fill, gap: 24 },
        [
          eyebrow("selection score", COLORS.darkblue),
          text("Weighted score combines closeness to best expert, IPC over disabled prefetching, margin over the worse expert, tail-loss penalty, and off-action penalty.", {
            name: "weighted-score-once",
            width: fill,
            height: hug,
            style: { fontSize: 31, color: COLORS.black, lineHeight: 1.16 },
          }),
          text("Candidate programs received failure scores for simulator failures, unknown policy keys, helper/import code, and missing evolve markers.", {
            name: "failure-score",
            width: fill,
            height: hug,
            style: { fontSize: 25, color: "#333333", lineHeight: 1.15 },
          }),
          resultTable(
            [
              ["Ledger", "Rows"],
              ["All candidates", "374"],
              ["Valid scored", "306"],
              ["Fail-closed", "68"],
            ],
            [fr(1.25), fr(0.75)],
            25,
          ),
        ],
      ),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 68, y: 54 }, gap: 18 },
    [
      title("Training-split validation is the main win", "Disabled prefetching is 1.000x. Dark blue is best expert, orange is MoP-V1, and pink is MoP-V2."),
      image({
        name: "pre-post-figure",
        dataUrl: pngDataUrl("stage2_pre_post_geomean.png"),
        contentType: "image/png",
        width: fill,
        height: fill,
        fit: "contain",
        alt: "Pre and post OpenEvolve geomean bars",
      }),
      figureCaption("Caption: The 13-trace validation bars show the main gain from MoP-V1 to MoP-V2. The 7-trace heldout bars show the smaller post-selection result. Prefetcher off is black at 1.000x and best expert is dark blue."),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(0.88), fr(1.12)],
      rows: [auto, fr(1)],
      columnGap: 48,
      rowGap: 24,
      padding: { x: 72, y: 54 },
    },
    [
      title("The numeric result is stronger on training than heldout", "Training-split validation carries the quantitative weight. Heldout supports a modest generalization claim."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "numeric-left", width: fill, height: fill, gap: 24 },
        [
          resultTable(
            [
              ["Surface", "MoP-V1", "MoP-V2", "Best expert"],
              ["13-trace speedup", "1.048x", "1.066x", "1.085x"],
              ["13-trace % best", "96.5%", "98.3%", "100.0%"],
              ["Beats worse expert", "9/13", "11/13", ""],
              ["Below 95% best", "3/13", "2/13", ""],
              ["7-heldout speedup", "0.998x", "1.003x", "1.024x"],
              ["7-heldout % best", "97.6%", "97.9%", "100.0%"],
            ],
            [fr(1.2), fr(0.58), fr(0.58), fr(0.74)],
            21,
          ),
          text("The IPC movement is cycle movement under a fixed retired-instruction window: MoP-V2 has instruction-count ratio 1.000x on both final runs, with cycle-count ratio 0.938x on training-split validation and 0.997x on heldout.", {
            name: "cycle-interpretation",
            width: fill,
            height: hug,
            style: { fontSize: 21, color: "#333333", lineHeight: 1.14 },
          }),
        ],
      ),
      column(
        { name: "win-loss-column", width: fill, height: fill, gap: 10 },
        [
          image({
            name: "win-loss",
            dataUrl: pngDataUrl("stage2_routing_behavior_stats.png"),
            contentType: "image/png",
            width: fill,
            height: fill,
            fit: "contain",
            alt: "Routing behavior stats for MoP-V1 and MoP-V2",
          }),
          figureCaption("Caption: The routing-behavior plot uses final run summaries to show selected-epoch share, budget share, and useful-prefetch share for MoP-V1 and MoP-V2."),
        ],
      ),
    ],
  ),
);

addSlide(
  column(
    { name: "root", width: fill, height: fill, padding: { x: 66, y: 52 }, gap: 18 },
    [
      title("Heldout behavior is trace-specific", "Within each heldout trace the profile order is Expert 1, Expert 2, MoP-V1, MoP-V2. The 1.000x line is disabled prefetching."),
      image({
        name: "heldout-profile",
        dataUrl: pngDataUrl("stage2_heldout_trace_profile.png"),
        contentType: "image/png",
        width: fill,
        height: fill,
        fit: "contain",
        alt: "Heldout trace profile with experts and router",
      }),
      figureCaption("Caption: The single experts share one blue hue with different opacity, MoP-V1 is orange, MoP-V2 is pink, and the black vertical line is disabled prefetching at 1.000x."),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(1.15), fr(0.85)],
      rows: [auto, fr(1)],
      columnGap: 50,
      rowGap: 24,
      padding: { x: 70, y: 54 },
    },
    [
      title("The expert pair gives routing something real to choose", "MLOP and SPP+PPF have different strengths across traces, so the router has a meaningful selection problem."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "expert-profile-column", width: fill, height: fill, gap: 10 },
        [
          image({
            name: "expert-profiles",
            dataUrl: pngDataUrl("stage2_heldout_trace_profile.png"),
            contentType: "image/png",
            width: fill,
            height: fill,
            fit: "contain",
            alt: "Heldout expert and router profile",
          }),
          figureCaption("Caption: The heldout trace profile shows where MLOP, SPP+PPF, MoP-V1, and MoP-V2 land relative to disabled prefetching at 1.000x."),
        ],
      ),
      column(
        { name: "expert-copy", width: fill, height: fill, gap: 22 },
        [
          metric("1.024x", "SPP+PPF heldout geomean over disabled prefetching", COLORS.darkblue, 62),
          metric("0.974x", "MLOP heldout geomean over disabled prefetching", COLORS.orange, 58),
          text("The best-expert reference is computed per trace, then geomeaned. It is a reference curve for routing quality.", {
            name: "best-expert-copy",
            width: fill,
            height: hug,
            style: { fontSize: 25, color: "#333333", lineHeight: 1.14 },
          }),
        ],
      ),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(0.78), fr(1.22)],
      rows: [auto, fr(1)],
      columnGap: 52,
      rowGap: 24,
      padding: { x: 70, y: 54 },
    },
    [
      title("MoP-V2 clears the simple router baselines", "WinnerTakeAll and OneShotFit are intentionally small baselines for the same expert pair."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "baseline-defs", width: fill, height: fill, gap: 18 },
        [
          keyValueRows(
            [
              ["WinnerTakeAll", "Picks the expert with the stronger previous-epoch usefulness score."],
              ["OneShotFit", "Probes the experts once, then keeps the better early winner."],
              ["Athena MAB", "Athena's multi-armed-bandit router baseline for the same expert pair."],
            ],
            [fr(0.72), fr(1.28)],
            23,
          ),
          resultTable(
            [
              ["13-trace method", "Speedup", "% best"],
              ["MoP-V2", "1.066x", "98.3%"],
              ["WinnerTakeAll", "1.025x", "94.3%"],
              ["OneShotFit", "1.027x", "94.3%"],
              ["Athena MAB", "1.021x", "94.2%"],
            ],
            [fr(1.25), fr(0.7), fr(0.65)],
            21,
          ),
        ],
      ),
      column(
        { name: "router-criterion-column", width: fill, height: fill, gap: 10 },
        [
          image({
            name: "router-criterion",
            dataUrl: pngDataUrl("stage2_pre_post_geomean.png"),
            contentType: "image/png",
            width: fill,
            height: fill,
            fit: "contain",
            alt: "MoP-V1 and MoP-V2 geomean comparison",
          }),
          figureCaption("Caption: MoP-V2 improves over MoP-V1 on the 13-trace validation set, while the heldout effect is smaller and shown after policy selection."),
        ],
      ),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(1.18), fr(0.82)],
      rows: [auto, fr(1)],
      columnGap: 48,
      rowGap: 24,
      padding: { x: 68, y: 52 },
    },
    [
      title("OpenEvolve found close candidates across models", "Quick-evaluation winners were similar, then wider validation and 13-trace confirmation selected MoP-V2."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "scale-model-column", width: fill, height: fill, gap: 10 },
        [
          image({
            name: "scale-models",
            dataUrl: pngDataUrl("stage2_scale_model_comparison.png"),
            contentType: "image/png",
            width: fill,
            height: fill,
            fit: "contain",
            alt: "Scaled model search and confirmation comparison",
          }),
          figureCaption("Caption: Faint points are quick-evaluation candidates. Dashed lines track the score-selected incumbent IPC, while solid lines track best IPC seen so far."),
        ],
      ),
      column(
        { name: "scale-copy", width: fill, height: fill, gap: 20 },
        [
          resultTable(
            [
              ["Model", "Iter", "Wide val"],
              ["GPT-5 mini", "80", "1.087x"],
              ["GPT-5.4", "80", "1.088x"],
              ["Sonnet 4.6", "30", "1.087x"],
            ],
            [fr(1.1), fr(0.48), fr(0.68)],
            22,
          ),
          text("The selected policy reached 1.089x on the same 10-trace wider-validation set, then 1.066x on the 13-trace training-split validation set.", {
            name: "selected-policy",
            width: fill,
            height: hug,
            style: { fontSize: 24, color: "#333333", lineHeight: 1.14 },
          }),
        ],
      ),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(1.05), fr(0.95)],
      rows: [auto, fr(1)],
      columnGap: 52,
      rowGap: 24,
      padding: { x: 72, y: 56 },
    },
    [
      title("Routing behavior remained interpretable", "MoP-V2 still acts like a compact epoch router, with observable action choices and budget behavior."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "action-distribution-column", width: fill, height: fill, gap: 10 },
        [
          image({
            name: "action-distribution",
            dataUrl: pngDataUrl("stage2_routing_behavior_stats.png"),
            contentType: "image/png",
            width: fill,
            height: fill,
            fit: "contain",
            alt: "Routing behavior shares from final runs",
          }),
          figureCaption("Caption: Final routing behavior stays interpretable: the plot shows how MoP-V1 and MoP-V2 allocate selected epochs, budget, and useful prefetches across the two experts."),
        ],
      ),
      column(
        { name: "action-copy", width: fill, height: fill, gap: 24 },
        [
          bulletList(
            [
              "The router can choose MLOP, SPP+PPF, both, or the off action after each epoch.",
              "The selected budget and score weights shape these choices without changing simulator internals.",
              "This keeps the final method inside a compact, auditable policy dictionary.",
            ],
            27,
          ),
          text("The report keeps raw implementation keys in writing_logistics.md so the main story can use public names.", {
            name: "logistics-pointer",
            width: fill,
            height: hug,
            style: { fontSize: 23, color: "#333333", lineHeight: 1.14 },
          }),
        ],
      ),
    ],
  ),
);

addSlide(
  grid(
    {
      name: "root",
      width: fill,
      height: fill,
      columns: [fr(1), fr(1)],
      rows: [auto, fr(1)],
      columnGap: 60,
      rowGap: 34,
      padding: { x: 92, y: 70 },
    },
    [
      title("Claim and limitations", "The final report makes a measured claim: strong training-split validation, small heldout lift, and transparent limits."),
      text("", { name: "blank-title-peer", width: fill, height: hug, style: { fontSize: 1, color: COLORS.white } }),
      column(
        { name: "claims", width: fill, height: fill, gap: 22 },
        [
          eyebrow("claims", COLORS.pink),
          bulletList(
            [
              "MoP-V2 improves over MoP-V1 on the 13-trace training-split validation set.",
              "MoP-V2 reaches 1.003x over disabled prefetching on seven heldout traces.",
              "Best expert remains a separate reference, with MoP-V2 reaching 97.9% of it on heldout.",
              "Instruction count stays fixed within simulator-rounding error.",
            ],
            26,
          ),
        ],
      ),
      column(
        { name: "limits", width: fill, height: fill, gap: 22 },
        [
          eyebrow("limits and reproduction", COLORS.darkblue),
          bulletList(
            [
              "Seven heldout traces make the heldout result a sanity check with visible per-trace variation.",
              "secret_compute_fp_105 remains the largest heldout loss relative to best expert.",
              "Malformed or out-of-contract OpenEvolve candidates stay in the candidate record with failure scores.",
              "Reproduction paths, naming map, and generated-file list live in report/writing_logistics.md.",
            ],
            26,
          ),
        ],
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

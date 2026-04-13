/**
 * Step 4 — Remotion Render
 * Bundles the Remotion project, selects the right composition,
 * injects the EditPlan as props, and renders to an MP4 file.
 */
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { EditPlan } from "../types.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export async function renderVideo(
  editPlan: EditPlan,
  format: "reels" | "youtube"
): Promise<string> {
  const compositionId = format === "reels" ? "Reels" : "YouTube";
  const outputDir = path.resolve(__dirname, "../../output");
  fs.mkdirSync(outputDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const outputPath = path.join(outputDir, `${format}_${timestamp}.mp4`);

  const entryPoint = path.resolve(__dirname, "../remotion-root.tsx");

  console.log("  Bundling Remotion project...");
  const bundleLocation = await bundle({
    entryPoint,
    // Pass environment variables for brand config into the bundle
    webpackOverride: (config) => {
      config.plugins = config.plugins ?? [];
      return config;
    },
  });

  console.log("  Selecting composition...");
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: compositionId,
    inputProps: { editPlan },
  });

  console.log(`  Rendering ${composition.width}×${composition.height} @ ${composition.fps}fps...`);
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation: outputPath,
    inputProps: { editPlan },
    onProgress: ({ progress }) => {
      const pct = Math.round(progress * 100);
      process.stdout.write(`\r  Progress: ${pct}%   `);
    },
  });

  process.stdout.write("\n");
  return outputPath;
}

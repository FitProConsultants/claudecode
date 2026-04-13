/**
 * Automated Video Editing Pipeline
 *
 * Usage:
 *   npm run pipeline -- --input ./raw/interview.mp4 --type reels
 *   npm run pipeline -- --input ./raw/tutorial.mp4  --type youtube
 *
 * What it does:
 *   1. Transcribe  — Extract audio → Whisper → timestamped transcript
 *   2. Analyze     — Claude reads transcript → edit plan (which segments, captions, title)
 *   3. Cut         — FFmpeg cuts selected segments from raw footage
 *   4. Render      — Remotion assembles clips + captions + intro/outro → final MP4
 */
import "dotenv/config";
import path from "path";
import fs from "fs";
import { transcribe } from "./transcribe.js";
import { analyze } from "./analyze.js";
import { cutClips } from "./cut.js";
import { renderVideo } from "./render.js";

// ── CLI argument parsing ─────────────────────────────────────────────────────

const args = process.argv.slice(2);

function getArg(flag: string): string | undefined {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : undefined;
}

const inputFile = getArg("--input");
const videoType = (getArg("--type") ?? "reels") as "reels" | "youtube";
const skipTranscribe = args.includes("--skip-transcribe");

if (!inputFile) {
  console.error(`
Usage:
  npm run pipeline -- --input <video.mp4> [--type reels|youtube]

Options:
  --input <path>     Path to raw footage file (MP4, MOV, etc.)
  --type  <format>   Output format: "reels" (default) or "youtube"

Examples:
  npm run pipeline -- --input ./raw/interview.mp4 --type reels
  npm run pipeline -- --input ./raw/tutorial.mp4  --type youtube
`);
  process.exit(1);
}

if (!fs.existsSync(inputFile)) {
  console.error(`Error: Input file not found: ${inputFile}`);
  process.exit(1);
}

if (videoType !== "reels" && videoType !== "youtube") {
  console.error(`Error: --type must be "reels" or "youtube", got "${videoType}"`);
  process.exit(1);
}

// ── Env validation ───────────────────────────────────────────────────────────

const missing: string[] = [];
if (!process.env.OPENAI_API_KEY) missing.push("OPENAI_API_KEY");
if (!process.env.ANTHROPIC_API_KEY) missing.push("ANTHROPIC_API_KEY");
if (missing.length > 0) {
  console.error(
    `Error: Missing environment variables: ${missing.join(", ")}\nCopy .env.example to .env and fill in your keys.`
  );
  process.exit(1);
}

// ── Pipeline ─────────────────────────────────────────────────────────────────

async function main() {
  console.log("\n========================================");
  console.log("  Automated Video Editing Pipeline");
  console.log("========================================");
  console.log(`  Input:  ${path.resolve(inputFile!)}`);
  console.log(`  Format: ${videoType.toUpperCase()}`);
  console.log("========================================\n");

  // ── Step 1: Transcribe ──────────────────────────────────────────────────
  console.log("[1/4] Transcribing audio with Whisper...");
  const transcript = await transcribe(path.resolve(inputFile!));
  console.log(
    `      Done — ${transcript.segments.length} segments, ${transcript.durationSeconds.toFixed(1)}s total\n`
  );

  // Save transcript for reference / debugging
  const transcriptPath = path.resolve(
    path.dirname(inputFile!),
    `transcript_${path.basename(inputFile!, path.extname(inputFile!))}.json`
  );
  fs.writeFileSync(transcriptPath, JSON.stringify(transcript, null, 2));
  console.log(`      Saved to: ${transcriptPath}\n`);

  // ── Step 2: Analyze with Claude ─────────────────────────────────────────
  console.log("[2/4] Creating edit plan with Claude...");
  const editPlan = await analyze(transcript, videoType);
  console.log();

  // Save edit plan for reference / debugging
  const planPath = path.resolve(
    path.dirname(inputFile!),
    `editplan_${videoType}_${path.basename(inputFile!, path.extname(inputFile!))}.json`
  );
  fs.writeFileSync(planPath, JSON.stringify(editPlan, null, 2));
  console.log(`      Saved to: ${planPath}\n`);

  // ── Step 3: Cut clips with FFmpeg ───────────────────────────────────────
  console.log("[3/4] Cutting clips with FFmpeg...");
  const clipsDir = path.resolve(__dirname, "../../public/clips");
  await cutClips(path.resolve(inputFile!), editPlan, clipsDir);
  console.log(`      ${editPlan.segments.length} clips written to: ${clipsDir}\n`);

  // ── Step 4: Render with Remotion ────────────────────────────────────────
  console.log("[4/4] Rendering final video with Remotion...");
  const outputPath = await renderVideo(editPlan, videoType);
  console.log(`      Done!\n`);

  console.log("========================================");
  console.log("  PIPELINE COMPLETE");
  console.log(`  Output: ${outputPath}`);
  if (editPlan.title) console.log(`  Title:  ${editPlan.title}`);
  if (editPlan.description) {
    console.log("\n  YouTube Description:");
    console.log(editPlan.description);
  }
  console.log("========================================\n");
}

main().catch((err) => {
  console.error("\nPipeline failed:", err.message);
  process.exit(1);
});

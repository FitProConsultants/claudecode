/**
 * Step 3 — FFmpeg Clip Cutting
 * Takes the raw footage and the EditPlan, cuts each selected segment
 * into its own clip file, and updates editPlan.segments[i].clipFile.
 */
import ffmpeg from "fluent-ffmpeg";
import path from "path";
import fs from "fs";
import { EditPlan } from "../types.js";

export async function cutClips(
  inputFile: string,
  editPlan: EditPlan,
  outputDir: string
): Promise<void> {
  fs.mkdirSync(outputDir, { recursive: true });

  // Remove any leftover clips from a previous run
  const existing = fs
    .readdirSync(outputDir)
    .filter((f) => f.startsWith("clip_") && f.endsWith(".mp4"));
  existing.forEach((f) => fs.unlinkSync(path.join(outputDir, f)));

  const isReels = editPlan.format === "reels";

  for (let i = 0; i < editPlan.segments.length; i++) {
    const seg = editPlan.segments[i];
    const clipFile = path.join(
      outputDir,
      `clip_${String(i + 1).padStart(3, "0")}.mp4`
    );

    const duration = seg.endSeconds - seg.startSeconds;
    console.log(
      `  [${i + 1}/${editPlan.segments.length}] Cutting ${seg.startSeconds.toFixed(1)}s–${seg.endSeconds.toFixed(1)}s (${duration.toFixed(1)}s)`
    );

    await cutClip(inputFile, seg.startSeconds, duration, clipFile, isReels);
    editPlan.segments[i].clipFile = clipFile;
  }
}

function cutClip(
  inputFile: string,
  startSeconds: number,
  durationSeconds: number,
  outputFile: string,
  verticalCrop: boolean
): Promise<void> {
  return new Promise((resolve, reject) => {
    let cmd = ffmpeg(inputFile)
      .seekInput(startSeconds)
      .duration(durationSeconds)
      .videoCodec("libx264")
      .audioCodec("aac")
      .outputOptions([
        "-preset fast",
        "-crf 20",
        "-movflags +faststart",
        "-pix_fmt yuv420p",
      ]);

    if (verticalCrop) {
      // For Reels: crop to 9:16 center of the frame
      // scale to height=1920, then center-crop to 1080 wide
      cmd = cmd.videoFilter(
        "scale=-2:1920,crop=1080:1920:(iw-1080)/2:0"
      );
    } else {
      // For YouTube: ensure 1920x1080, letterbox if needed
      cmd = cmd.videoFilter(
        "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
      );
    }

    cmd
      .output(outputFile)
      .on("end", () => resolve())
      .on("error", (err) =>
        reject(new Error(`FFmpeg cut error: ${err.message}`))
      )
      .run();
  });
}

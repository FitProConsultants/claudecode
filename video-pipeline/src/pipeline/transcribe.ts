/**
 * Step 1 — Transcription
 * Extracts audio from the raw video and sends it to OpenAI Whisper.
 * Returns a structured transcript with per-segment timestamps.
 */
import OpenAI from "openai";
import fs from "fs";
import path from "path";
import ffmpeg from "fluent-ffmpeg";
import { Transcript } from "../types.js";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function transcribe(videoPath: string): Promise<Transcript> {
  console.log("  Extracting audio from video...");
  const audioPath = path.join(
    path.dirname(videoPath),
    `_audio_${Date.now()}.mp3`
  );

  await extractAudio(videoPath, audioPath);

  console.log("  Sending audio to Whisper...");
  const audioStream = fs.createReadStream(audioPath);

  const response = await openai.audio.transcriptions.create({
    file: audioStream,
    model: "whisper-1",
    response_format: "verbose_json",
    timestamp_granularities: ["segment"],
  });

  // Clean up temp audio
  fs.unlinkSync(audioPath);

  const segments = (response.segments ?? []).map((seg) => ({
    start: seg.start,
    end: seg.end,
    text: seg.text.trim(),
  }));

  const durationSeconds = segments.at(-1)?.end ?? 0;

  return { segments, fullText: response.text, durationSeconds };
}

function extractAudio(videoPath: string, audioPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    ffmpeg(videoPath)
      .noVideo()
      .audioCodec("libmp3lame")
      .audioBitrate("128k")
      .output(audioPath)
      .on("end", () => resolve())
      .on("error", (err) => reject(new Error(`FFmpeg audio extract: ${err.message}`)))
      .run();
  });
}

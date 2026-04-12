#!/usr/bin/env node
/**
 * transcribe.js
 *
 * Usage:
 *   node scripts/transcribe.js <video-file> [output.json]
 *
 * Extracts audio via FFmpeg, sends to OpenAI Whisper (verbose_json),
 * and writes a word-level transcript JSON ready for use in Remotion.
 *
 * Requires: OPENAI_API_KEY env var
 */

import {execSync} from 'child_process';
import {createReadStream, writeFileSync, unlinkSync, existsSync} from 'fs';
import path from 'path';
import OpenAI from 'openai';

const [,, videoFile, outputFile] = process.argv;

if (!videoFile) {
  console.error('Usage: node scripts/transcribe.js <video-file> [output.json]');
  process.exit(1);
}

if (!process.env.OPENAI_API_KEY) {
  console.error('Error: OPENAI_API_KEY environment variable is not set.');
  process.exit(1);
}

const openai = new OpenAI({apiKey: process.env.OPENAI_API_KEY});

const audioFile = videoFile.replace(/\.[^.]+$/, '') + '_audio.mp3';
const out = outputFile ?? videoFile.replace(/\.[^.]+$/, '') + '_transcript.json';

// Step 1: Extract audio
console.log(`Extracting audio from ${videoFile}...`);
execSync(
  `ffmpeg -y -i "${videoFile}" -vn -ar 16000 -ac 1 -b:a 64k "${audioFile}"`,
  {stdio: 'inherit'},
);

// Step 2: Transcribe with Whisper
console.log('Sending to Whisper API...');
const transcription = await openai.audio.transcriptions.create({
  file: createReadStream(audioFile),
  model: 'whisper-1',
  response_format: 'verbose_json',
  timestamp_granularities: ['word'],
});

// Step 3: Build clean output
const result = {
  text: transcription.text,
  duration: transcription.duration,
  language: transcription.language,
  words: (transcription.words ?? []).map((w) => ({
    word: w.word,
    start: w.start,  // seconds
    end: w.end,      // seconds
  })),
  segments: (transcription.segments ?? []).map((s) => ({
    text: s.text,
    start: s.start,
    end: s.end,
  })),
};

writeFileSync(out, JSON.stringify(result, null, 2));
console.log(`Transcript written to ${out}`);
console.log(`  ${result.words.length} words, ${result.duration?.toFixed(1)}s`);

// Cleanup temp audio
if (existsSync(audioFile)) unlinkSync(audioFile);

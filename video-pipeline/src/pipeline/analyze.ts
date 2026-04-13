/**
 * Step 2 — AI Analysis with Claude
 * Reads the transcript and returns a structured EditPlan:
 * which segments to keep, captions, title, hook.
 *
 * Uses prompt caching on the system prompt to reduce cost on repeated runs.
 */
import Anthropic from "@anthropic-ai/sdk";
import { Transcript, EditPlan } from "../types.js";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You are a professional video editor and social media strategist.
Your job is to analyze a raw video transcript and create a precise, data-driven edit plan.

You understand:
- Instagram/TikTok Reels: hook-first, fast-paced, 30-60 seconds, subtitles always on
- YouTube videos: complete value delivery, clear structure, can be up to 10+ minutes

Return ONLY valid JSON that matches the schema exactly. No explanations, no markdown fences.`;

export async function analyze(
  transcript: Transcript,
  format: "reels" | "youtube"
): Promise<EditPlan> {
  const isReels = format === "reels";
  const targetDuration = isReels ? "30–60 seconds" : "as long as needed (max 10 min)";

  const transcriptText = transcript.segments
    .map((s) => `[${s.start.toFixed(1)}s–${s.end.toFixed(1)}s] ${s.text}`)
    .join("\n");

  const userPrompt = `FORMAT: ${format.toUpperCase()}
TARGET DURATION: ${targetDuration}
SOURCE VIDEO LENGTH: ${transcript.durationSeconds.toFixed(1)}s

TRANSCRIPT:
${transcriptText}

Create an edit plan. Return this JSON schema exactly:
{
  "title": "string — compelling title for the video",
  ${isReels ? '"hook": "string — 5-8 word opening hook that appears on the intro card",' : '"description": "string — YouTube description with timestamps (format: MM:SS Title)\\n...",'}
  "segments": [
    {
      "startSeconds": 0.0,
      "endSeconds": 5.0,
      "reason": "string — why this segment is included"
    }
  ],
  "captions": [
    {
      "startSeconds": 0.0,
      "endSeconds": 3.5,
      "text": "string — 3-6 words shown on screen"
    }
  ]
}

RULES:
${isReels
    ? `- Select only the BEST moments totalling 30–60 seconds
- Lead with the most attention-grabbing segment — viewers decide in 2 seconds
- Cut filler words, pauses, and repetition aggressively
- Every caption must be punchy: max 6 words, high contrast, easy to read`
    : `- Keep ALL valuable content — do not over-cut
- Organize into clear sections (intro, main points, conclusion)
- Include natural breathing room between points
- Captions should match the spoken words exactly for accessibility`
  }
- Never exceed the source video duration in segment timestamps
- Segment gaps are OK (jump cuts) — they will be edited together
- Caption timing must fall within the selected segments (not in cut sections)`;

  console.log("  Calling Claude for edit plan...");

  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4096,
    system: [
      {
        type: "text",
        text: SYSTEM_PROMPT,
        // Prompt caching: system prompt is static, cache it to save tokens
        cache_control: { type: "ephemeral" },
      },
    ],
    messages: [{ role: "user", content: userPrompt }],
  });

  const block = message.content[0];
  if (block.type !== "text") {
    throw new Error("Unexpected response type from Claude");
  }

  // Strip potential markdown fences
  const raw = block.text.replace(/```(?:json)?/g, "").trim();
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`No JSON found in Claude response:\n${block.text}`);
  }

  const plan = JSON.parse(jsonMatch[0]) as Omit<EditPlan, "totalDurationSeconds" | "format">;

  const totalDurationSeconds = plan.segments.reduce(
    (sum, seg) => sum + (seg.endSeconds - seg.startSeconds),
    0
  );

  console.log(
    `  Edit plan ready: ${plan.segments.length} segments, ${totalDurationSeconds.toFixed(1)}s of content`
  );
  console.log(`  Title: "${plan.title}"`);

  return { ...plan, totalDurationSeconds, format };
}

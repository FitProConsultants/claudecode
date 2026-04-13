// ---------------------------------------------------------------------------
// Transcript types (output of Whisper)
// ---------------------------------------------------------------------------

export interface TranscriptSegment {
  start: number;  // seconds
  end: number;    // seconds
  text: string;
}

export interface Transcript {
  segments: TranscriptSegment[];
  fullText: string;
  durationSeconds: number;
}

// ---------------------------------------------------------------------------
// Edit plan types (output of Claude analysis)
// ---------------------------------------------------------------------------

export interface EditSegment {
  startSeconds: number;
  endSeconds: number;
  reason: string;
  /** Absolute path to the cut clip file — populated by cutClips() */
  clipFile?: string;
}

export interface CaptionEntry {
  startSeconds: number;
  endSeconds: number;
  text: string;
}

export interface EditPlan {
  title: string;
  /** Short hook shown in the intro card (Reels only) */
  hook?: string;
  /** Full description with timestamps (YouTube only) */
  description?: string;
  segments: EditSegment[];
  captions: CaptionEntry[];
  /** Computed total seconds of content (excluding intro/outro) */
  totalDurationSeconds: number;
  format: "reels" | "youtube";
}

// ---------------------------------------------------------------------------
// Remotion composition props
// ---------------------------------------------------------------------------

export interface CompositionProps {
  editPlan: EditPlan;
}

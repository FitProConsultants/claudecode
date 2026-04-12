/**
 * Transcript types and helpers for mapping speech timing to Remotion frames.
 */

export interface Word {
  word: string;
  start: number; // seconds
  end: number;   // seconds
}

export interface Segment {
  text: string;
  start: number;
  end: number;
}

export interface Transcript {
  text: string;
  duration: number;
  language: string;
  words: Word[];
  segments: Segment[];
}

/** Convert seconds to Remotion frames */
export const secToFrame = (seconds: number, fps: number): number =>
  Math.round(seconds * fps);

/**
 * Find the word index where a search phrase first appears in the transcript.
 * Returns the frame at which that word starts.
 */
export const frameForPhrase = (
  phrase: string,
  words: Word[],
  fps: number,
): number | null => {
  const lower = phrase.toLowerCase();
  const idx = words.findIndex((w) =>
    w.word.toLowerCase().includes(lower),
  );
  if (idx === -1) return null;
  return secToFrame(words[idx].start, fps);
};

/**
 * Build a list of {from, durationInFrames} graphic cues from the transcript.
 * Each cue appears when the trigger phrase is spoken and stays for `holdSecs`.
 */
export interface GraphicCue {
  label: string;
  from: number;       // frame
  durationInFrames: number;
}

export const buildCues = (
  triggers: Array<{label: string; phrase: string; holdSecs?: number}>,
  words: Word[],
  fps: number,
  defaultHoldSecs = 4,
): GraphicCue[] => {
  return triggers
    .map(({label, phrase, holdSecs = defaultHoldSecs}) => {
      const from = frameForPhrase(phrase, words, fps);
      if (from === null) return null;
      return {label, from, durationInFrames: Math.round(holdSecs * fps)};
    })
    .filter((c): c is GraphicCue => c !== null);
};

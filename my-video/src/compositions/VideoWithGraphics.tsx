/**
 * VideoWithGraphics — the master composition template.
 *
 * Usage:
 *   1. Drop your video file in public/ (e.g. public/video.mp4)
 *   2. Add your transcript JSON path
 *   3. Define graphicCues — each maps a frame range to a graphic component
 *
 * The video plays as background. Graphic overlays appear at the right timestamps
 * using <Sequence> components keyed to word-level Whisper timestamps.
 */
import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, useVideoConfig} from 'remotion';
import {BulletList} from '../components/BulletList';
import {ComparisonCard} from '../components/ComparisonCard';
import {ProcessFlow} from '../components/ProcessFlow';
import {StatCard} from '../components/StatCard';
import type {GraphicCue} from '../lib/transcript';

// ---------------------------------------------------------------------------
// CONFIGURE THESE per video
// ---------------------------------------------------------------------------

/** Path to your video file in public/ */
const VIDEO_SRC = staticFile('video.mp4');

/**
 * Graphic cues — define when each overlay appears.
 * `from` = frame number (use secToFrame(seconds, fps) from lib/transcript).
 * `durationInFrames` = how long it stays.
 *
 * Replace these examples with cues built from your transcript.
 */
const GRAPHIC_CUES: Array<GraphicCue & {graphic: React.ReactNode}> = [
  // Example: bullet list at frame 90 (3s @ 30fps), stays 5s
  {
    label: 'intro-list',
    from: 90,
    durationInFrames: 150,
    graphic: (
      <BulletList
        title="What We Cover"
        items={['Point one', 'Point two', 'Point three']}
      />
    ),
  },
  // Example: stat callout at frame 300 (10s), stays 4s
  {
    label: 'stat-1',
    from: 300,
    durationInFrames: 120,
    graphic: <StatCard value="87%" label="of users saw results" subLabel="based on 2024 study" />,
  },
  // Example: comparison at frame 540 (18s), stays 6s
  {
    label: 'comparison-1',
    from: 540,
    durationInFrames: 180,
    graphic: (
      <ComparisonCard
        title="Before vs. After"
        left={{label: 'Before', points: ['Slow process', 'Manual work', 'High cost'], color: '#FF4444'}}
        right={{label: 'After', points: ['Automated', 'Faster output', 'Lower cost'], color: '#00C2FF'}}
      />
    ),
  },
];

// ---------------------------------------------------------------------------

export const VideoWithGraphics: React.FC = () => {
  const {durationInFrames} = useVideoConfig();

  return (
    <AbsoluteFill style={{background: '#000'}}>
      {/* Background video */}
      <OffthreadVideo src={VIDEO_SRC} style={{width: '100%', height: '100%', objectFit: 'cover'}} />

      {/* Graphic overlays keyed to transcript timestamps */}
      {GRAPHIC_CUES.map((cue) =>
        cue.from < durationInFrames ? (
          <Sequence
            key={cue.label}
            from={cue.from}
            durationInFrames={Math.min(cue.durationInFrames, durationInFrames - cue.from)}
            name={cue.label}
          >
            {cue.graphic}
          </Sequence>
        ) : null,
      )}
    </AbsoluteFill>
  );
};

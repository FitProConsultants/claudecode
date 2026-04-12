/**
 * BulletList — animated bullet list overlay.
 * Items stagger in from the left, one per ~15 frames.
 */
import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface Props {
  title?: string;
  items: string[];
  accentColor?: string;
  staggerFrames?: number;
}

export const BulletList: React.FC<Props> = ({
  title,
  items,
  accentColor = '#00C2FF',
  staggerFrames = 12,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        background: 'rgba(10,10,20,0.88)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '80px 100px',
      }}
    >
      {title && (
        <div
          style={{
            color: accentColor,
            fontSize: 52,
            fontWeight: 800,
            fontFamily: 'sans-serif',
            marginBottom: 48,
            opacity: interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'}),
            transform: `translateY(${interpolate(frame, [0, 10], [20, 0], {extrapolateRight: 'clamp'})}px)`,
          }}
        >
          {title}
        </div>
      )}
      {items.map((item, i) => {
        const delay = i * staggerFrames;
        const progress = spring({
          frame: frame - delay,
          fps,
          config: {damping: 14, stiffness: 120},
        });
        return (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 24,
              marginBottom: 28,
              opacity: progress,
              transform: `translateX(${interpolate(progress, [0, 1], [-60, 0])}px)`,
            }}
          >
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: accentColor,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                color: '#ffffff',
                fontSize: 38,
                fontFamily: 'sans-serif',
                fontWeight: 500,
                lineHeight: 1.4,
              }}
            >
              {item}
            </span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

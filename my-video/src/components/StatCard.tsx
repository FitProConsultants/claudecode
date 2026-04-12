/**
 * StatCard — large number / stat callout with animated count-up.
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
  value: string;   // e.g. "47%" or "$1.2M" or "3x"
  label: string;
  subLabel?: string;
  accentColor?: string;
}

export const StatCard: React.FC<Props> = ({
  value,
  label,
  subLabel,
  accentColor = '#00C2FF',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({frame, fps, config: {damping: 12, stiffness: 90}});
  const labelProgress = spring({frame: frame - 12, fps, config: {damping: 14, stiffness: 100}});

  return (
    <AbsoluteFill
      style={{
        background: 'rgba(10,10,20,0.88)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
      }}
    >
      <div
        style={{
          color: accentColor,
          fontSize: 160,
          fontWeight: 900,
          fontFamily: 'sans-serif',
          lineHeight: 1,
          opacity: entrance,
          transform: `scale(${interpolate(entrance, [0, 1], [0.5, 1])})`,
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: '#ffffff',
          fontSize: 48,
          fontWeight: 700,
          fontFamily: 'sans-serif',
          textAlign: 'center',
          opacity: labelProgress,
          transform: `translateY(${interpolate(labelProgress, [0, 1], [20, 0])}px)`,
        }}
      >
        {label}
      </div>
      {subLabel && (
        <div
          style={{
            color: '#888888',
            fontSize: 30,
            fontFamily: 'sans-serif',
            textAlign: 'center',
            opacity: interpolate(frame, [20, 30], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {subLabel}
        </div>
      )}
    </AbsoluteFill>
  );
};

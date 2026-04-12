/**
 * ComparisonCard — side-by-side comparison (Before vs After, A vs B, etc.)
 */
import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface Side {
  label: string;
  points: string[];
  color?: string;
}

interface Props {
  title?: string;
  left: Side;
  right: Side;
}

const Panel: React.FC<{side: Side; delay: number; slideFrom: 'left' | 'right'}> = ({
  side,
  delay,
  slideFrom,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = spring({frame: frame - delay, fps, config: {damping: 16, stiffness: 100}});
  const dir = slideFrom === 'left' ? -1 : 1;

  return (
    <div
      style={{
        flex: 1,
        background: `${side.color ?? '#1a1a2e'}cc`,
        border: `2px solid ${side.color ?? '#444'}`,
        borderRadius: 16,
        padding: '40px 44px',
        opacity: progress,
        transform: `translateX(${interpolate(progress, [0, 1], [dir * 80, 0])}px)`,
      }}
    >
      <div
        style={{
          color: side.color ?? '#00C2FF',
          fontSize: 36,
          fontWeight: 800,
          fontFamily: 'sans-serif',
          marginBottom: 32,
          textTransform: 'uppercase',
          letterSpacing: 2,
        }}
      >
        {side.label}
      </div>
      {side.points.map((p, i) => (
        <div
          key={i}
          style={{
            color: '#e0e0e0',
            fontSize: 28,
            fontFamily: 'sans-serif',
            marginBottom: 16,
            lineHeight: 1.5,
          }}
        >
          • {p}
        </div>
      ))}
    </div>
  );
};

export const ComparisonCard: React.FC<Props> = ({title, left, right}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background: 'rgba(10,10,20,0.88)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 80px',
        gap: 24,
      }}
    >
      {title && (
        <div
          style={{
            color: '#ffffff',
            fontSize: 48,
            fontWeight: 800,
            fontFamily: 'sans-serif',
            textAlign: 'center',
            marginBottom: 16,
            opacity: interpolate(frame, [0, 12], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {title}
        </div>
      )}
      <div style={{display: 'flex', gap: 32, flex: 1}}>
        <Panel side={left} delay={8} slideFrom="left" />
        <Panel side={right} delay={16} slideFrom="right" />
      </div>
    </AbsoluteFill>
  );
};

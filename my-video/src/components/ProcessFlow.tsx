/**
 * ProcessFlow — numbered step-by-step process animation.
 * Each step reveals sequentially with a connecting line.
 */
import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface Step {
  number?: number;
  title: string;
  description?: string;
}

interface Props {
  title?: string;
  steps: Step[];
  accentColor?: string;
  staggerFrames?: number;
}

export const ProcessFlow: React.FC<Props> = ({
  title,
  steps,
  accentColor = '#00C2FF',
  staggerFrames = 15,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        background: 'rgba(10,10,20,0.90)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 100px',
      }}
    >
      {title && (
        <div
          style={{
            color: '#ffffff',
            fontSize: 50,
            fontWeight: 800,
            fontFamily: 'sans-serif',
            marginBottom: 48,
            opacity: interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {title}
        </div>
      )}
      {steps.map((step, i) => {
        const delay = i * staggerFrames;
        const progress = spring({
          frame: frame - delay,
          fps,
          config: {damping: 14, stiffness: 110},
        });
        const isLast = i === steps.length - 1;

        return (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 28,
              opacity: progress,
              transform: `translateY(${interpolate(progress, [0, 1], [30, 0])}px)`,
              marginBottom: isLast ? 0 : 24,
            }}
          >
            {/* Number badge + connector */}
            <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: '50%',
                  background: accentColor,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#000',
                  fontSize: 24,
                  fontWeight: 800,
                  fontFamily: 'sans-serif',
                  flexShrink: 0,
                }}
              >
                {step.number ?? i + 1}
              </div>
              {!isLast && (
                <div
                  style={{
                    width: 2,
                    flex: 1,
                    minHeight: 24,
                    background: `${accentColor}55`,
                    marginTop: 6,
                  }}
                />
              )}
            </div>
            {/* Text */}
            <div style={{paddingTop: 10}}>
              <div
                style={{
                  color: '#ffffff',
                  fontSize: 32,
                  fontWeight: 700,
                  fontFamily: 'sans-serif',
                  lineHeight: 1.3,
                }}
              >
                {step.title}
              </div>
              {step.description && (
                <div
                  style={{
                    color: '#aaaaaa',
                    fontSize: 24,
                    fontFamily: 'sans-serif',
                    marginTop: 6,
                    lineHeight: 1.5,
                  }}
                >
                  {step.description}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

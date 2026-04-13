import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface OutroProps {
  format: "reels" | "youtube";
  ctaText?: string;
}

export const Outro: React.FC<OutroProps> = ({ format, ctaText }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const brandName = process.env.BRAND_NAME ?? "Brand";
  const brandColor = process.env.BRAND_COLOR ?? "#FF4500";

  const isReels = format === "reels";
  const defaultCta = isReels ? "Follow for more" : "Subscribe for more";
  const callToAction = ctaText ?? defaultCta;

  const scaleIn = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 140, mass: 1 },
  });

  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });

  const ctaFade = interpolate(frame, [15, 28], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)`,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 28,
      }}
    >
      {/* Brand name */}
      <div
        style={{
          color: "#ffffff",
          fontSize: isReels ? 80 : 90,
          fontWeight: 900,
          fontFamily: "'Helvetica Neue', Arial, sans-serif",
          letterSpacing: "4px",
          textTransform: "uppercase",
          opacity: fadeIn,
          transform: `scale(${0.6 + scaleIn * 0.4})`,
        }}
      >
        {brandName}
      </div>

      {/* Accent line */}
      <div
        style={{
          width: interpolate(frame, [8, 25], [0, 160], {
            extrapolateRight: "clamp",
          }),
          height: 4,
          background: brandColor,
          borderRadius: 2,
        }}
      />

      {/* CTA */}
      <div
        style={{
          color: brandColor,
          fontSize: isReels ? 42 : 36,
          fontWeight: 700,
          fontFamily: "'Helvetica Neue', Arial, sans-serif",
          opacity: ctaFade,
        }}
      >
        {callToAction}
      </div>
    </AbsoluteFill>
  );
};

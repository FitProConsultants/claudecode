import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface IntroProps {
  title: string;
  format: "reels" | "youtube";
}

export const Intro: React.FC<IntroProps> = ({ title, format }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const brandName = process.env.BRAND_NAME ?? "Brand";
  const brandColor = process.env.BRAND_COLOR ?? "#FF4500";

  const titleY = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 160, mass: 0.8 },
  });

  const titleOpacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });

  const brandOpacity = interpolate(frame, [10, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const isReels = format === "reels";

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)`,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: isReels ? 32 : 24,
        padding: isReels ? "60px 60px" : "40px 80px",
      }}
    >
      {/* Accent bar */}
      <div
        style={{
          width: 72,
          height: 6,
          background: brandColor,
          borderRadius: 3,
          opacity: brandOpacity,
        }}
      />

      {/* Hook / Title */}
      <div
        style={{
          color: "#ffffff",
          fontSize: isReels ? 72 : 80,
          fontWeight: 900,
          fontFamily: "'Helvetica Neue', Arial, sans-serif",
          textAlign: "center",
          lineHeight: 1.15,
          maxWidth: "85%",
          opacity: titleOpacity,
          transform: `translateY(${(1 - titleY) * 40}px)`,
          textShadow: "0 4px 16px rgba(0,0,0,0.5)",
        }}
      >
        {title}
      </div>

      {/* Brand name */}
      <div
        style={{
          color: brandColor,
          fontSize: isReels ? 36 : 32,
          fontWeight: 700,
          fontFamily: "'Helvetica Neue', Arial, sans-serif",
          letterSpacing: "3px",
          textTransform: "uppercase",
          opacity: brandOpacity,
        }}
      >
        {brandName}
      </div>
    </AbsoluteFill>
  );
};

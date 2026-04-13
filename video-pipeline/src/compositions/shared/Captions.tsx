import React from "react";
import {
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";
import { CaptionEntry } from "../../types";

interface CaptionsProps {
  captions: CaptionEntry[];
  /** How many seconds of intro precede the content (for offset calculation) */
  introSeconds: number;
}

export const Captions: React.FC<CaptionsProps> = ({
  captions,
  introSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const contentSeconds = (frame - introSeconds * fps) / fps;

  const active = captions.find(
    (c) => contentSeconds >= c.startSeconds && contentSeconds < c.endSeconds
  );

  const opacity = active
    ? interpolate(
        contentSeconds - active.startSeconds,
        [0, 0.15],
        [0, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      )
    : 0;

  if (!active && opacity === 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 180,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        padding: "0 60px",
        pointerEvents: "none",
        opacity,
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.72)",
          color: "#ffffff",
          fontSize: 52,
          fontWeight: 800,
          fontFamily: "'Helvetica Neue', Arial, sans-serif",
          lineHeight: 1.25,
          padding: "18px 36px",
          borderRadius: 16,
          maxWidth: "90%",
          textAlign: "center",
          textShadow: "0 2px 8px rgba(0,0,0,0.6)",
          letterSpacing: "-0.5px",
        }}
      >
        {active?.text}
      </div>
    </div>
  );
};

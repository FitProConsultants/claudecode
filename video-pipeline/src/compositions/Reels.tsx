/**
 * Reels composition — 1080×1920 (9:16 vertical), up to 90 seconds.
 *
 * Layout:
 *   [Intro card 2s] → [clip 1] → [clip 2] → ... → [Outro 3s]
 *   Captions overlay throughout the content section.
 */
import React from "react";
import { AbsoluteFill, Series, OffthreadVideo } from "remotion";
import { CompositionProps } from "../types";
import { Intro } from "./shared/Intro";
import { Outro } from "./shared/Outro";
import { Captions } from "./shared/Captions";

const INTRO_SECONDS = 2;
const OUTRO_SECONDS = 3;
const FPS = 30;

export const Reels: React.FC<CompositionProps> = ({ editPlan }) => {
  const introFrames = INTRO_SECONDS * FPS;
  const outroFrames = OUTRO_SECONDS * FPS;

  const segmentsWithFrames = (editPlan?.segments ?? []).map((seg) => ({
    ...seg,
    durationFrames: Math.max(
      1,
      Math.round((seg.endSeconds - seg.startSeconds) * FPS)
    ),
  }));

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Series>
        {/* ── Intro ── */}
        <Series.Sequence durationInFrames={introFrames}>
          <Intro
            title={editPlan?.hook ?? editPlan?.title ?? "Watch this"}
            format="reels"
          />
        </Series.Sequence>

        {/* ── Content clips ── */}
        {segmentsWithFrames.map((seg, i) => (
          <Series.Sequence key={i} durationInFrames={seg.durationFrames}>
            <AbsoluteFill>
              {seg.clipFile ? (
                <OffthreadVideo
                  src={seg.clipFile}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : (
                // Placeholder when no clip file (e.g. during Remotion Studio preview)
                <AbsoluteFill
                  style={{
                    background: "#111",
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  <span style={{ color: "#555", fontSize: 36 }}>
                    Clip {i + 1}
                  </span>
                </AbsoluteFill>
              )}
            </AbsoluteFill>
          </Series.Sequence>
        ))}

        {/* ── Outro ── */}
        <Series.Sequence durationInFrames={outroFrames}>
          <Outro format="reels" />
        </Series.Sequence>
      </Series>

      {/* ── Captions overlay ── */}
      {editPlan?.captions && (
        <Captions
          captions={editPlan.captions}
          introSeconds={INTRO_SECONDS}
        />
      )}
    </AbsoluteFill>
  );
};

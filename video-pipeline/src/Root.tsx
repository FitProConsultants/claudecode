import React from "react";
import { Composition, CalculateMetadataFunction } from "remotion";
import { Reels } from "./compositions/Reels";
import { YouTube } from "./compositions/YouTube";
import { CompositionProps } from "./types";

const FPS = 30;

// Reels: 2s intro + content + 3s outro  (max 90s total)
const calculateReelsMeta: CalculateMetadataFunction<CompositionProps> = async ({
  props,
}) => {
  if (!props.editPlan) {
    return { durationInFrames: 90 * FPS, fps: FPS, width: 1080, height: 1920 };
  }
  const total =
    2 + // intro
    props.editPlan.totalDurationSeconds +
    3; // outro
  return {
    durationInFrames: Math.ceil(total * FPS),
    fps: FPS,
    width: 1080,
    height: 1920,
  };
};

// YouTube: 3s intro + content + 5s outro
const calculateYouTubeMeta: CalculateMetadataFunction<CompositionProps> = async ({
  props,
}) => {
  if (!props.editPlan) {
    return {
      durationInFrames: 600 * FPS,
      fps: FPS,
      width: 1920,
      height: 1080,
    };
  }
  const total =
    3 + // intro
    props.editPlan.totalDurationSeconds +
    5; // outro
  return {
    durationInFrames: Math.ceil(total * FPS),
    fps: FPS,
    width: 1920,
    height: 1080,
  };
};

const defaultProps: CompositionProps = {
  editPlan: {
    title: "Preview Mode",
    hook: "Preview Mode",
    segments: [],
    captions: [],
    totalDurationSeconds: 10,
    format: "reels",
  },
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Reels"
        component={Reels}
        calculateMetadata={calculateReelsMeta}
        durationInFrames={90 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
      />
      <Composition
        id="YouTube"
        component={YouTube}
        calculateMetadata={calculateYouTubeMeta}
        durationInFrames={600 * FPS}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ ...defaultProps, editPlan: { ...defaultProps.editPlan, format: "youtube" } }}
      />
    </>
  );
};

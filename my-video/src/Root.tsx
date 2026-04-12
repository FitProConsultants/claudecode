import React from 'react';
import {Composition} from 'remotion';
import {VideoWithGraphics} from './compositions/VideoWithGraphics';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/*
        VideoWithGraphics — edit durationInFrames to match your video length.
        Formula: durationInFrames = totalSeconds * fps
        e.g. 60s video at 30fps = 1800 frames
      */}
      <Composition
        id="VideoWithGraphics"
        component={VideoWithGraphics}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

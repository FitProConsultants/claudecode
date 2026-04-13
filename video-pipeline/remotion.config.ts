import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);

// Codec: h264 for broad compatibility (social media, YouTube)
Config.setCodec("h264");

// CRF: lower = better quality, larger file (18-28 is a good range)
Config.setCrf(22);

import React from "react";
import { ShaderGradientCanvas, ShaderGradient } from "@shadergradient/react";
export default function AmbientGradient({ url }) {
  return <ShaderGradientCanvas style={{ position: "absolute", inset: 0 }} pointerEvents="none" fov={45} pixelDensity={1}>
    <ShaderGradient control="query" urlString={url} animate="on" />
  </ShaderGradientCanvas>;
}

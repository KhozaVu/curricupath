/* Atmosphere — the WebGL layer.
 *
 *   ShaderGradient  (react-three-fiber)  → the ambient moving gradient behind the page
 *   LiquidMetal     (@paper-design)      → the chrome brand mark in the masthead
 *   LiquidGlass     (CSS + SVG filter)   → Apple-style refracting panels
 *
 * Every piece is decorative and degrades to a flat colour. Nothing here renders
 * curriculum data, and none of it is required to read a decision — see DESIGN.md §2.
 */
import React, { lazy, Suspense, useEffect, useState } from "react";
const LiquidMetal = lazy(()=>import("@paper-design/shaders-react").then(m=>({default:m.LiquidMetal})));
const AmbientGradient = lazy(() => import("./AmbientGradient"));
import { hasWebGL } from "./webgl";
import { GraphicsBoundary } from "./GraphicsBoundary";
const prefersReducedMotion = () => {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
};
/* ---------------------------------------------------------------- gradient */
/* Environmental light. One canvas; the palette carries application state.
   See CURRICUPATH-DESIGN.md §8. */
const scene = (c1, c2, c3, speed, bg) =>
  "https://www.shadergradient.co/customize?animate=on&axesHelper=off" +
  `&bgColor1=%23${bg}&bgColor2=%23${bg}&brightness=0.9&cAzimuthAngle=180&cDistance=3.6` +
  "&cPolarAngle=90&cameraZoom=1" +
  `&color1=%23${c1}&color2=%23${c2}&color3=%23${c3}` +
  "&destination=onCanvas&embedMode=off&envPreset=city&format=gif&fov=45&frameRate=10" +
  "&grain=on&lightType=3d&pixelDensity=1&positionX=-1.4&positionY=0&positionZ=0" +
  "&range=enabled&rangeEnd=40&rangeStart=0&reflection=0.1&rotationX=0&rotationY=10" +
  `&rotationZ=50&shader=defaults&type=waterPlane&uAmplitude=0&uDensity=1.3&uFrequency=5.5&uSpeed=${speed}` +
  "&uStrength=4&uTime=0&wireframe=false";
const MOODS = {
  /* page            c1        c2        c3       speed   bg */
  profile: scene("1c1c20", "2b2d34", "15161a", 0.08, "000000"), // quiet graphite
  home: scene("34588c", "cb944e", "53688e", 0.18, "0a1428"), // visible campus blue and lamp glow
  journey: scene("0b1230", "1a2b55", "070a18", 0.1, "000000"), // spatial blue
  advisor: scene("1a1430", "2d2a52", "0d0b1a", 0.13, "000000"), // smoky violet
  library: scene("12202a", "1e3a44", "0a1218", 0.09, "000000"), // cool teal
  careers: scene("201a12", "3a2f1e", "14100a", 0.09, "000000"), // warm bronze
  evidence: scene("0d1a18", "16322c", "060f0e", 0.08, "000000"), // verified teal
  light: scene("e8e2d6", "cfd8e3", "f3efe7", 0.1, "ffffff"),
};
/* The campus plate is the ground; the shader is the light that moves over it.
   Three layers: photograph, animated shader tint, readability scrim.
   See CURRICUPATH-DESIGN.md §8. */
export function Atmosphere({
  theme = "dark",
  mood = "profile",
  reducedMotion = false,
  motionLevel = "subtle",
}) {
  const still = reducedMotion || prefersReducedMotion();
  const webgl = hasWebGL();
  const [active, setActive] = useState(false);
  const [campusVisible, setCampusVisible] = useState(true);
  useEffect(() => {
    const hero = document.querySelector(".campus-hero");
    if (!hero || !window.IntersectionObserver) {setCampusVisible(true);return;}
    const observer = new IntersectionObserver(([entry])=>setCampusVisible(entry.isIntersecting),{rootMargin:"80px"});
    observer.observe(hero);
    return ()=>observer.disconnect();
  },[mood]);
  const [visible, setVisible] = useState(!document.hidden);
  useEffect(() => {
    const media = window.matchMedia(
      "(min-width: 900px) and (prefers-reduced-motion: no-preference)",
    );
    const update = () => {
      setVisible(!document.hidden);
      setActive(media.matches && !document.hidden);
    };
    update();
    media.addEventListener("change", update);
    document.addEventListener("visibilitychange", update);
    return () => {
      media.removeEventListener("change", update);
      document.removeEventListener("visibilitychange", update);
    };
  }, []);
  return (
    <div className={`atmosphere mood-${mood}`} aria-hidden="true">
      <div className={`atmosphere-plate ${still ? "is-still" : ""}`} />
      {webgl && active && campusVisible && !still && motionLevel === "expressive" && mood === "home" && (
        <div className="atmosphere-light">
          <GraphicsBoundary>
            <Suspense fallback={null}>
              <AmbientGradient
                url={
                  theme === "light" ? MOODS.light : MOODS[mood] || MOODS.profile
                }
              />
            </Suspense>
          </GraphicsBoundary>
        </div>
      )}
      <div className="atmosphere-scrim" />
      {!still && (
        <div className={`campus-light-trails ${visible ? "" : "is-paused"}`}>
          <span className="campus-light-trail trail-amber" />
          <span className="campus-light-trail trail-blue" />
          <span className="campus-light-trail trail-pearl" />
        </div>
      )}
    </div>
  );
}
/* ------------------------------------------------------------ liquid metal */
export function LiquidMark({
  size = 40,
  state = "idle",
  reducedMotion = false,
}) {
  const [ok, setOk] = useState(true);
  const [hidden, setHidden] = useState(document.hidden);
  useEffect(() => {
    const update = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  if (!ok || reducedMotion || prefersReducedMotion() || !hasWebGL())
    return (
      <span
        className="liquid-mark liquid-mark-fallback"
        style={{ width: size, height: size }}
      />
    );
  try {
    return (
      <span className="liquid-mark" style={{ width: size, height: size }}>
        <GraphicsBoundary><Suspense fallback={null}><LiquidMetal
          style={{ width: size, height: size }}
          colorBack="#00000000"
          colorTint="#dfe6f0"
          shape="circle"
          repetition={state === "thinking" ? 6 : 4}
          softness={0.3}
          shiftRed={0.3}
          shiftBlue={-0.3}
          distortion={state === "thinking" ? 0.42 : 0.12}
          contour={0.9}
          speed={
            hidden || reducedMotion || prefersReducedMotion()
              ? 0
              : state === "thinking"
                ? 1.6
                : state === "verified"
                  ? 0.9
                  : 0.25
          }
        /></Suspense></GraphicsBoundary>
      </span>
    );
  } catch {
    setOk(false);
    return (
      <span
        className="liquid-mark liquid-mark-fallback"
        style={{ width: size, height: size }}
      />
    );
  }
}
/* ------------------------------------------------------------- liquid glass */
/* The SVG displacement map that gives panels their edge refraction.
   Mounted once; panels reference it with backdrop-filter: url(#liquid-glass). */
export function LiquidGlassFilter() {
  return (
    <svg className="glass-filter-defs" aria-hidden="true" focusable="false">
      <defs>
        <filter
          id="liquid-glass"
          x="-20%"
          y="-20%"
          width="140%"
          height="140%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.008 0.012"
            numOctaves="2"
            seed="7"
            result="noise"
          />
          <feGaussianBlur in="noise" stdDeviation="2.4" result="softNoise" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="softNoise"
            scale="42"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  );
}

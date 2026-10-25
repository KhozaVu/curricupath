/* CurriculumMap — the curriculum as a navigable 3D dependency graph.
 *
 * react-three-fiber + drei. Nodes are modules, placed on a ring per year of study;
 * edges are prerequisite and corequisite rules read from /programmes/{code}/graph.
 * Nothing here is inferred — a module with no recorded rule simply has no edge.
 *
 * Motion follows selection. The chosen prerequisite chain stays emphasized
 * while unrelated links recede; orbit and zoom remain under student control.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  AdaptiveDpr,
  Billboard,
  Line,
  OrbitControls,
  Text,
} from "@react-three/drei";
import * as THREE from "three";

import { hasWebGL } from "./webgl";
import { graphForView } from "./planModel.mjs";
const prefersReducedMotion = () => {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
};

/* scratch objects reused every frame — never allocate inside useFrame (R3F perf guide) */
const SCRATCH = new THREE.Vector3();

const YEAR_GAP = 5.2;
const RING_RADIUS = 10.5;

const NODE_GEOMETRY = new THREE.IcosahedronGeometry(0.7, 1);

const STATUS_COLOR = {
  completed: "#3fb950",
  current: "#6db3e8",
  planned: "#a78bfa",
  repeating: "#e0a93c",
  none: "#5c5f66",
};

function layout(nodes) {
  const byYear = new Map();
  for (const n of nodes) {
    const y = Number(n.year_of_study) || 1;
    if (!byYear.has(y)) byYear.set(y, []);
    byYear.get(y).push(n);
  }
  const placed = new Map();
  const years = [...byYear.keys()].sort((a, b) => a - b);
  const mid = (years[0] + years[years.length - 1]) / 2;
  for (const year of years) {
    const ring = byYear.get(year);
    ring.forEach((n, i) => {
      const angle = (i / ring.length) * Math.PI * 2 + year * 0.4;
      placed.set(n.course_code, {
        ...n,
        pos: [
          Math.cos(angle) * RING_RADIUS,
          (year - mid) * YEAR_GAP,
          Math.sin(angle) * RING_RADIUS,
        ],
      });
    });
  }
  return placed;
}

function Node({
  node,
  status,
  dim,
  active,
  onHover,
  onSelect,
  reducedMotion,
  showLabel,
}) {
  const ref = useRef();
  const colour = STATUS_COLOR[status] || STATUS_COLOR.none;
  useFrame(({ invalidate }) => {
    if (!ref.current) return;

    const target = active ? 1.5 : dim ? 0.72 : 1;
    SCRATCH.set(target, target, target);
    if (reducedMotion || prefersReducedMotion())
      ref.current.scale.copy(SCRATCH);
    else if (ref.current.scale.distanceTo(SCRATCH) > 0.002) {
      ref.current.scale.lerp(SCRATCH, 0.12);
      invalidate();
    }
  });
  return (
    <group position={node.pos}>
      <mesh
        ref={ref}
        geometry={NODE_GEOMETRY}
        onPointerOver={(e) => {
          e.stopPropagation();
          onHover(node.course_code);
        }}
        onPointerOut={() => onHover(null)}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(node.course_code);
        }}
      >
        <meshStandardMaterial
          color={colour}
          emissive={colour}
          emissiveIntensity={active ? 2.2 : dim ? 0.1 : 0.95}
          roughness={0.18}
          metalness={0.75}
          transparent
          opacity={dim ? 0.35 : 1}
        />
      </mesh>
      {active && (
        <Billboard>
          <mesh>
            <ringGeometry args={[1.35, 1.42, 32]} />
            <meshBasicMaterial color="#eef3ff" transparent opacity={0.9} />
          </mesh>
        </Billboard>
      )}
      {(showLabel ||
        active ||
        ["planned", "current", "repeating"].includes(status)) && (
        <Billboard position={[0, 1.5, 0]}>
          <Text
            fontSize={0.62}
            color="#f6f4f0"
            anchorX="center"
            outlineWidth={0.03}
            outlineColor="#000"
          >
            {node.course_code}
          </Text>
          {active && (
            <Text
              position={[0, -0.72, 0]}
              fontSize={0.38}
              color="#a6a29b"
              anchorX="center"
              maxWidth={11}
            >
              {node.course_name || ""}
            </Text>
          )}
        </Billboard>
      )}
    </group>
  );
}

function YearRing({ year, y, count }) {
  return (
    <group position={[0, y, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[RING_RADIUS - 0.04, RING_RADIUS + 0.04, 96]} />
        <meshBasicMaterial
          color="#3a3d44"
          transparent
          opacity={0.4}
          side={THREE.DoubleSide}
        />
      </mesh>
      <Billboard position={[RING_RADIUS + 2.6, 0, 0]}>
        <Text
          fontSize={0.92}
          color="#a2afc2"
          anchorX="left"
        >{`YEAR ${year}`}</Text>
        <Text
          position={[0, -0.8, 0]}
          fontSize={0.52}
          color="#a2afc2"
          anchorX="left"
        >{`${count} modules`}</Text>
      </Billboard>
    </group>
  );
}

const CAM_TARGET = new THREE.Vector3();
const CAM_POS = new THREE.Vector3();

/* Eases the camera toward a selected node and back out again. Reuses two
   module-scoped vectors; nothing is allocated per frame. */
function CameraRig({
  placed,
  selected,
  controls,
  resetKey,
  reducedMotion,
  frame,
}) {
  const last = useRef(undefined);
  const lastReset = useRef(resetKey);
  const lastFrame = useRef(null);
  const moving = useRef(false);
  useFrame(({ camera, invalidate }) => {
    if (!controls.current) return;
    if (
      last.current !== selected ||
      lastReset.current !== resetKey ||
      lastFrame.current !== frame
    ) {
      lastFrame.current = frame;
      const resetting = lastReset.current !== resetKey;
      lastReset.current = resetKey;
      last.current = selected;
      const node = !resetting && selected ? placed.get(selected) : null;
      if (node) {
        CAM_TARGET.set(...node.pos);
        CAM_POS.set(node.pos[0] + 12, node.pos[1] + 8, node.pos[2] + 24);
      } else {
        CAM_TARGET.set(...frame.target);
        CAM_POS.set(...frame.position);
      }
      moving.current = true;
    }
    if (!moving.current) return;
    const speed = reducedMotion || prefersReducedMotion() ? 1 : 0.08;
    camera.position.lerp(CAM_POS, speed);
    controls.current.target.lerp(CAM_TARGET, speed);
    controls.current.update();
    if (camera.position.distanceTo(CAM_POS) < 0.1) moving.current = false;
    else invalidate();
  });
  return null;
}

function Scene({
  graph,
  fullGraph,
  profile,
  hovered,
  setHovered,
  onSelect,
  selected,
  controls,
  highlight = [],
  mode,
  resetKey,
  reducedMotion,
  showLabels,
  focus,
}) {
  const placed = useMemo(() => layout(fullGraph.nodes), [fullGraph]);
  const group = useRef();
  const frame = useMemo(() => {
    const box = new THREE.Box3();
    graph.nodes.forEach((node) =>
      box.expandByPoint(new THREE.Vector3(...placed.get(node.course_code).pos)),
    );
    // Include the year rings and their captions in the visible frame.
    graph.nodes.forEach((node) => {
      const y = placed.get(node.course_code).pos[1];
      box.expandByPoint(new THREE.Vector3(-RING_RADIUS, y - 1, -RING_RADIUS));
      box.expandByPoint(new THREE.Vector3(RING_RADIUS + 7, y + 1, RING_RADIUS));
    });
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const distance = Math.max(30, Math.max(size.x, size.y, size.z) * 1.8);
    return {
      target: center.toArray(),
      position: [
        center.x + distance * 0.45,
        center.y + distance * 0.28,
        center.z + distance * 0.88,
      ],
    };
  }, [graph.nodes.map(node=>node.course_code).join("|"), placed]);

  const statusOf = (code) => {
    if (profile.completed?.includes(code)) return "completed";
    if (profile.current?.includes(code)) return "current";
    if (profile.planned?.includes(code)) return "planned";
    if (profile.repeating?.includes(code)) return "repeating";
    return "none";
  };

  /* the chain lit when a module is hovered: itself plus everything it depends on */
  const chain = useMemo(() => {
    const focus = selected;
    const seeds = focus ? [focus] : highlight;
    if (!seeds.length) return null;
    const keep = new Set(seeds);
    let grew = true;
    while (grew) {
      grew = false;
      for (const e of graph.edges) {
        if (keep.has(e.to) && !keep.has(e.from)) {
          keep.add(e.from);
          grew = true;
        }
      }
    }
    return keep;
  }, [selected, highlight, graph]);

  const years = useMemo(() => {
    const m = new Map();
    for (const item of graph.nodes) {
      const n = placed.get(item.course_code);
      const y = Number(n.year_of_study) || 1;
      if (!m.has(y)) m.set(y, { y: n.pos[1], count: 0 });
      m.get(y).count += 1;
    }
    return m;
  }, [placed, graph]);

  return (
    <>
      <ambientLight intensity={1.1} />
      <hemisphereLight args={["#9fb6ff", "#1a1a1f", 1.2]} />
      <pointLight position={[14, 18, 14]} intensity={420} color="#9fb6ff" />
      <pointLight position={[-16, -12, -8]} intensity={260} color="#e0a93c" />
      <CameraRig
        placed={placed}
        frame={frame}
        selected={
          !focus && graph.nodes.some((node) => node.course_code === selected)
            ? selected
            : null
        }
        controls={controls}
        resetKey={resetKey}
        reducedMotion={reducedMotion}
      />
      <group ref={group}>
        {[...years.entries()].map(([year, info]) => (
          <YearRing key={year} year={year} y={info.y} count={info.count} />
        ))}

        {graph.edges.map((e, i) => {
          const a = placed.get(e.from);
          const b = placed.get(e.to);
          if (!a || !b) return null;
          const lit = chain ? chain.has(e.from) && chain.has(e.to) : false;
          return (
            <Line
              key={`${e.from}-${e.to}-${i}`}
              points={[a.pos, b.pos]}
              color={
                lit
                  ? e.kind === "corequisite"
                    ? "#e0a93c"
                    : "#6db3e8"
                  : "#464a52"
              }
              lineWidth={lit ? 2.6 : 1}
              transparent
              opacity={
                chain ? (lit ? 1 : 0.035) : mode === "dependencies" ? 0.32 : 0.1
              }
              dashed={e.kind === "corequisite"}
              dashScale={3}
            />
          );
        })}

        {graph.nodes.map((item) => {
          const n = placed.get(item.course_code);
          return (
            <Node
              reducedMotion={reducedMotion}
              showLabel={
                graph.edges.some(edge=>edge.to === selected && edge.from === n.course_code) || showLabels ||
                (graph.nodes.length <= 8 &&
                  (!chain || chain.has(n.course_code)))
              }
              key={n.course_code}
              node={n}
              status={statusOf(n.course_code)}
              active={
                hovered === n.course_code ||
                selected === n.course_code ||
                (!hovered && !selected && highlight.includes(n.course_code))
              }
              dim={Boolean(chain) && !chain.has(n.course_code)}
              onHover={setHovered}
              onSelect={onSelect}
            />
          );
        })}
      </group>
    </>
  );
}

export function CurriculumMap({
  programme,
  profile,
  onOpenModule,
  selected,
  highlight = [],
  mode = "study",
  data,
  year = null,
  focus = false,
  resetKey = 0,
  reducedMotion = false,
  showLabels = false,
}) {
  const [loadedGraph, setGraph] = useState(null);
  const graph = data === undefined ? loadedGraph : data;
  const [hovered, setHovered] = useState(null);
  const [error, setError] = useState(null);
  const controls = useRef(null);
  const [retry, setRetry] = useState(0);
  const webgl = useMemo(() => hasWebGL(), []);

  useEffect(() => {
    if (!programme || data !== undefined) return;
    setGraph(null);
    setError(null);
    let alive = true;
    fetch(`/programmes/${programme}/graph`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("unavailable"))))
      .then((d) => {
        if (alive) setGraph(d);
      })
      .catch(() => {
        if (alive) setError("The curriculum map could not be loaded.");
      });
    return () => {
      alive = false;
    };
  }, [programme, retry, data]);

  if (!programme)
    return (
      <div className="empty-panel">Choose a programme to see its map.</div>
    );
  if (error)
    return (
      <div className="map-loading" role="alert">
        {error}
        <button
          className="secondary-button"
          onClick={() => setRetry((n) => n + 1)}
        >
          Try again
        </button>
      </div>
    );
  if (!graph)
    return <div className="empty-panel">Building the curriculum map…</div>;

  const visibleGraph = graphForView(
    graph,
    profile,
    mode,
    selected,
    highlight,
    year,
    focus,
  );
  if (!visibleGraph.nodes.length)
    return (
      <div className="map-loading">
        <h2>
          {year
            ? "No selected modules in this year."
            : "A plan starts with one module."}
        </h2>
        <p>
          Switch to Dependencies to explore your programme, or choose a module
          from the list below.
        </p>
      </div>
    );

  const counts = visibleGraph.edges.reduce(
    (acc, e) => ({ ...acc, [e.kind]: (acc[e.kind] || 0) + 1 }),
    {},
  );

  if (!webgl) {
    const byYear = visibleGraph.nodes.reduce((acc, n) => {
      (acc[n.year_of_study] ||= []).push(n);
      return acc;
    }, {});
    const incoming = (code) => graph.edges.filter((e) => e.to === code);
    return (
      <div className="map-fallback">
        <p className="sm">
          3D is unavailable in this browser, so the curriculum map is shown as a
          list. This view includes {visibleGraph.nodes.length} modules and{" "}
          {visibleGraph.edges.length} recorded links.
        </p>
        {Object.entries(byYear).map(([year, items]) => (
          <section key={year}>
            <h3>Year {year}</h3>
            <ul>
              {items.map((n) => {
                const needs = incoming(n.course_code);
                return (
                  <li key={n.course_code}>
                    <button
                      type="button"
                      onClick={() => onOpenModule(n.course_code)}
                    >
                      <strong>{n.course_code}</strong> {n.course_name}
                    </button>
                    {needs.length > 0 && (
                      <span className="needs">
                        needs {needs.map((e) => e.from).join(", ")}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    );
  }

  return (
    <div className="curriculum-map">
      <Canvas
        frameloop="demand"
        camera={{ position: [24, 14, 48], fov: 36 }}
        dpr={[1, window.matchMedia("(max-width: 700px)").matches ? 1 : 1.5]}
        performance={{ min: 0.4 }}
      >
        <Scene
          graph={visibleGraph}
          fullGraph={graph}
          profile={profile}
          hovered={hovered}
          setHovered={setHovered}
          onSelect={onOpenModule}
          selected={selected}
          controls={controls}
          highlight={highlight}
          mode={mode}
          resetKey={resetKey}
          reducedMotion={reducedMotion}
          showLabels={showLabels}
          focus={focus}
        />
        <AdaptiveDpr pixelated />
        <OrbitControls
          ref={controls}
          enablePan={false}
          autoRotate={false}
          minDistance={26}
          maxDistance={110}
          enableDamping={!reducedMotion && !prefersReducedMotion()}
          dampingFactor={0.08}
        />
      </Canvas>

      <div className="map-legend">
        <span className="map-hint">
          Drag to orbit · select a module to light its prerequisite chain ·
          click to open it
        </span>
        <div className="map-keys">
          <span>
            <i style={{ background: STATUS_COLOR.completed }} />
            Completed
          </span>

          <span>
            <i style={{ background: STATUS_COLOR.current }} />
            Current
          </span>
          <span>
            <i style={{ background: STATUS_COLOR.repeating }} />
            Repeating
          </span>
          <span>
            <i style={{ background: STATUS_COLOR.none }} />
            Not selected
          </span>
          <span>
            <i style={{ background: STATUS_COLOR.planned }} />
            Planned
          </span>
          <span>
            <i
              style={{
                background: "transparent",
                border: "1px solid #eef3ff",
                width: 10,
                height: 10,
              }}
            />
            Selected
          </span>
        </div>
        <div className="map-link-keys">
          <span>
            <i />
            Prerequisite
          </span>
          <span className="corequisite">
            <i />
            Corequisite
          </span>
        </div>
        <span className="map-count">
          {visibleGraph.nodes.length} of {graph.nodes.length} modules ·{" "}
          {counts.prerequisite || 0} prerequisite and {counts.corequisite || 0}{" "}
          corequisite links, all from recorded rules
        </span>
      </div>
    </div>
  );
}

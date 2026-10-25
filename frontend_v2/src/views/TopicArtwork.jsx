import React, { useId } from "react";

// Original vector illustrations. Decorative; the button supplies the accessible name.
export function TopicArtwork({ topic }) {
  const id = useId().replaceAll(":", "");
  const layers = [[58, [58, 100, 142]], [124, [38, 79, 121, 162]], [190, [58, 100, 142]], [248, [100]]];
  const network = [[150, 98], [80, 42], [231, 52], [257, 143], [95, 157], [35, 104]];
  return (
    <svg className="topic-artwork" viewBox="0 0 300 200" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id={`${id}-glow`}>
          <stop stopColor="var(--topic-color)" stopOpacity=".2" />
          <stop offset="1" stopColor="var(--topic-color)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}-metal`} x1="90" y1="50" x2="220" y2="170" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--topic-color)" stopOpacity=".45" />
          <stop offset=".55" stopColor="var(--topic-color)" stopOpacity=".08" />
          <stop offset="1" stopColor="var(--topic-color)" stopOpacity=".3" />
        </linearGradient>
      </defs>
      <ellipse cx="150" cy="102" rx="146" ry="98" fill={`url(#${id}-glow)`} />
      <g className="topic-drawing" stroke="var(--topic-color)">
        {topic === "learning" && <>
          {layers.slice(0, -1).flatMap(([x, ys], i) => ys.flatMap((y, j) => layers[i + 1][1].map((nextY, k) =>
            <path key={`${i}-${j}-${k}`} d={`M${x} ${y} C${x + 30} ${y},${layers[i + 1][0] - 30} ${nextY},${layers[i + 1][0]} ${nextY}`} opacity=".24" />
          )))}
          {layers.flatMap(([x, ys], i) => ys.map((y, j) => <g key={`${i}-${j}`}>
            <circle cx={x} cy={y} r={i === 3 ? 13 : 8} fill="var(--topic-ground)" strokeWidth="1.5" />
            <circle cx={x} cy={y} r={i === 3 ? 5 : 2.5} fill="var(--topic-color)" stroke="none" />
          </g>))}
          <path d="M35 181H265" opacity=".15" />
        </>}
        {topic === "networks" && <>
          <ellipse cx="150" cy="100" rx="109" ry="73" strokeDasharray="3 7" opacity=".25" />
          <ellipse cx="150" cy="100" rx="68" ry="93" transform="rotate(55 150 100)" opacity=".16" />
          {network.slice(1).map(([x, y], i) => <path key={i} d={`M150 98L${x} ${y}`} opacity=".5" />)}
          <path d="M80 42L231 52L257 143L95 157L35 104L80 42" opacity=".22" />
          {network.map(([x, y], i) => <g key={i}>
            <circle cx={x} cy={y} r={i === 0 ? 25 : 11} fill="var(--topic-ground)" strokeWidth="1.5" />
            {i === 0 && <circle cx={x} cy={y} r="17" opacity=".4" />}
            <circle cx={x} cy={y} r={i === 0 ? 6 : 3} fill="var(--topic-color)" stroke="none" />
          </g>)}
        </>}
        {topic === "embedded" && <>
          <path d="M71 58L169 25L236 68L139 104Z" fill={`url(#${id}-metal)`} strokeWidth="1.5" />
          <path d="M71 58V129L139 174V104M139 174L236 139V68" fill={`url(#${id}-metal)`} strokeWidth="1.5" />
          <path d="M112 62L167 43L199 64L144 83Z" fill="var(--topic-ground)" />
          <path d="M126 63L166 49L185 62L146 76Z" opacity=".6" />
          {[0, 1, 2, 3].map(i => <g key={i} opacity=".6">
            <path d={`M${86 + i * 12} ${69 + i * 8}V${122 + i * 8}L${62 + i * 12} ${138 + i * 8}`} />
            <path d={`M${157 + i * 19} ${104 - i * 7}V${157 - i * 7}L${173 + i * 19} ${171 - i * 7}`} />
            <circle cx={62 + i * 12} cy={138 + i * 8} r="2" fill="var(--topic-color)" stroke="none" />
            <circle cx={173 + i * 19} cy={171 - i * 7} r="2" fill="var(--topic-color)" stroke="none" />
          </g>)}
        </>}
      </g>
    </svg>
  );
}

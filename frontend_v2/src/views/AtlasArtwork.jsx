import React, { useId } from "react";

// Original decorative geometry: campus gateways, conversation and possible paths.
// These illustrations never represent curriculum relationships or eligibility.
export function AtlasArtwork({ variant = "gateway", className = "" }) {
  const id = useId().replaceAll(":", "");
  return (
    <svg className={`atlas-artwork ${className}`} viewBox="0 0 300 230" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-light`} x1="40" y1="15" x2="260" y2="215" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--atlas-metal)" stopOpacity=".38" />
          <stop offset=".55" stopColor="var(--atlas-metal)" stopOpacity=".03" />
          <stop offset="1" stopColor="var(--atlas-metal)" stopOpacity=".18" />
        </linearGradient>
      </defs>
      <g stroke="var(--atlas-metal)" strokeWidth="1.15">
        <path d="M24 206H276M150 16V214" opacity=".16" strokeDasharray="2 7" />
        {variant === "gateway" && <>
          <path d="M65 192V101a85 85 0 0 1 170 0v91Z" fill={`url(#${id}-light)`} />
          <path d="M82 192V101a68 68 0 0 1 136 0v91M99 192V101a51 51 0 0 1 102 0v91M116 192V101a34 34 0 0 1 68 0v91" opacity=".65" />
          <path d="M44 193H256M54 201H246M64 209H236" opacity=".55" />
          <path d="M150 184V128m-7 7 7-7 7 7" strokeWidth="1.8" />
          <circle cx="150" cy="91" r="4" fill="var(--atlas-metal)" />
        </>}
        {variant === "path" && <>
          <ellipse cx="150" cy="166" rx="104" ry="35" opacity=".22" />
          <ellipse cx="150" cy="120" rx="80" ry="28" opacity=".35" />
          <ellipse cx="150" cy="72" rx="56" ry="21" opacity=".55" />
          <path className="atlas-route-stroke" d="M53 167C62 144 237 157 228 120S85 112 96 73S191 58 170 36" strokeWidth="2" />
          {[[53,167],[228,120],[96,73],[170,36]].map(([x,y],i)=><g key={i}><circle cx={x} cy={y} r="8" fill="var(--atlas-ground)" /><circle cx={x} cy={y} r="2.5" fill="var(--atlas-metal)" /></g>)}
        </>}
        {variant === "dialogue" && <>
          <path d="M45 118V93a65 65 0 0 1 130 0v74l-30-19H75a30 30 0 0 1-30-30Z" fill={`url(#${id}-light)`} />
          <path d="M124 136V116a55 55 0 0 1 110 0v44a28 28 0 0 1-28 28h-50l-32 19v-36" fill="var(--atlas-ground)" />
          <path d="M76 90h65M76 106h42M149 121h58M149 137h39" opacity=".65" />
          <circle cx="182" cy="165" r="4" fill="var(--atlas-metal)" />
          <path d="M195 165h10" opacity=".5" />
        </>}
        {variant === "orbit" && <>
          <circle cx="150" cy="114" r="74" opacity=".6" />
          <ellipse cx="150" cy="114" rx="112" ry="38" transform="rotate(-32 150 114)" fill={`url(#${id}-light)`} />
          <ellipse cx="150" cy="114" rx="112" ry="38" transform="rotate(32 150 114)" opacity=".4" />
          <circle cx="150" cy="114" r="24" fill="var(--atlas-ground)" />
          <path d="m140 124 20-20m-13 0h13v13" strokeWidth="1.8" />
          <circle cx="87" cy="76" r="5" fill="var(--atlas-metal)" />
          <circle cx="213" cy="152" r="5" fill="var(--atlas-metal)" />
        </>}
      </g>
    </svg>
  );
}

export function ChapterKicker({ index, children }) {
  return <span className="eyebrow chapter-kicker"><span className="chapter-index" aria-hidden="true">{index}</span><span>{children}</span></span>;
}

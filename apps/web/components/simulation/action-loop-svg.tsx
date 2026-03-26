"use client";

/* ------------------------------------------------------------------ */
/*  SENSE -> THINK -> PLAN -> ACT action loop ring                     */
/* ------------------------------------------------------------------ */

export type Phase = "SENSE" | "THINK" | "PLAN" | "ACT" | "IDLE";

interface ActionLoopSvgProps {
  activePhase: Phase;
  size?: number;
}

const PHASES: { label: Phase; startAngle: number; color: string }[] = [
  { label: "SENSE", startAngle: -90, color: "#3B82F6" },
  { label: "THINK", startAngle: 0, color: "#A855F7" },
  { label: "PLAN", startAngle: 90, color: "#F97316" },
  { label: "ACT", startAngle: 180, color: "#22C55E" },
];

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const start = polarToCartesian(cx, cy, r, startDeg);
  const end = polarToCartesian(cx, cy, r, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;
}

export default function ActionLoopSvg({ activePhase, size = 120 }: ActionLoopSvgProps) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const gap = 4; // degrees gap between arcs
  const arcSpan = 90 - gap;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      {PHASES.map((phase) => {
        const isActive = activePhase === phase.label;
        const startDeg = phase.startAngle + gap / 2;
        const endDeg = phase.startAngle + arcSpan;
        const d = arcPath(cx, cy, r, startDeg, endDeg);

        // Label position at midpoint of arc
        const midDeg = phase.startAngle + 45;
        const labelR = r + size * 0.13;
        const labelPos = polarToCartesian(cx, cy, labelR, midDeg);

        return (
          <g key={phase.label}>
            {/* Arc */}
            <path
              d={d}
              fill="none"
              stroke={isActive ? phase.color : "#334155"}
              strokeWidth={isActive ? 6 : 4}
              strokeLinecap="round"
              className={isActive ? "animate-pulse" : ""}
            />
            {/* Label */}
            <text
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fill={isActive ? phase.color : "#64748B"}
              fontSize={size * 0.075}
              fontWeight={isActive ? 700 : 500}
              fontFamily="monospace"
            >
              {phase.label}
            </text>
          </g>
        );
      })}

      {/* Center text */}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fill={activePhase === "IDLE" ? "#64748B" : "#F8FAFC"}
        fontSize={size * 0.1}
        fontWeight={700}
        fontFamily="monospace"
      >
        {activePhase}
      </text>
    </svg>
  );
}

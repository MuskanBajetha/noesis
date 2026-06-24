"use client";

import { useEffect, useRef, useState } from "react";

/**
 * The shared progression primitive for the whole dashboard — replaces every
 * plain progress bar. A thin metallic line with a glowing endpoint; on mount
 * (or value change) a spark travels the line's length once, then settles.
 */
export default function GoldThread({
  value, // 0-100
  label,
  sublabel,
  accent = "gold", // "gold" | "slate" — which accent family this thread uses
  height = 3,
}: {
  value: number;
  label?: string;
  sublabel?: string;
  accent?: "gold" | "slate";
  height?: number;
}) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const [sparking, setSparking] = useState(false);
  const prevValue = useRef(0);

  const colors = accent === "gold"
    ? { line: "#D4A574", glow: "rgba(212, 165, 116, 0.55)", dim: "#3D2817" }
    : { line: "#7FA3B8", glow: "rgba(127, 163, 184, 0.5)", dim: "#2A3640" };

  useEffect(() => {
    // Animate the fill from its previous value to the new one
    const start = prevValue.current;
    const end = value;
    prevValue.current = value;

    if (start === end) return;

    setSparking(true);
    const duration = 900;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setAnimatedValue(start + (end - start) * eased);

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        setTimeout(() => setSparking(false), 400);
      }
    };
    requestAnimationFrame(tick);
  }, [value]);

  return (
    <div className="space-y-1.5">
      {(label || sublabel) && (
        <div className="flex items-baseline justify-between text-xs">
          {label && <span className="text-[#F5F0E8]/70 font-medium">{label}</span>}
          {sublabel && <span className="text-[#F5F0E8]/40">{sublabel}</span>}
        </div>
      )}
      <div className="relative" style={{ height: height + 8 }}>
        {/* Base line, dim */}
        <div
          className="absolute top-1/2 left-0 right-0 -translate-y-1/2 rounded-full"
          style={{ height, background: colors.dim }}
        />
        {/* Filled portion */}
        <div
          className="absolute top-1/2 left-0 -translate-y-1/2 rounded-full transition-none"
          style={{
            height,
            width: `${animatedValue}%`,
            background: `linear-gradient(90deg, ${colors.dim}, ${colors.line})`,
          }}
        />
        {/* Glowing endpoint */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full transition-none"
          style={{
            left: `${animatedValue}%`,
            width: height + 6, height: height + 6,
            background: colors.line,
            boxShadow: sparking ? `0 0 12px 3px ${colors.glow}` : `0 0 4px 1px ${colors.glow}`,
            transition: "box-shadow 0.4s ease-out",
          }}
        />
        {/* Traveling spark, only visible while animating */}
        {sparking && (
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full"
            style={{
              left: `${animatedValue}%`,
              width: 5, height: 5,
              background: "#F5F0E8",
              boxShadow: `0 0 8px 2px ${colors.glow}`,
              opacity: 0.9,
            }}
          />
        )}
      </div>
    </div>
  );
}
"use client";

/**
 * A small ribbon/bookmark marker indicating revision priority.
 * Priority 1 (weak) = full gold ribbon. Priority 2 (past misconception) =
 * half-gold. Priority 3 (needs revision) = outline only. This maps urgency
 * to "how much gold ink has been applied," echoing a manuscript marginalia
 * marker rather than a generic colored dot.
 */
export function RevisionBookmark({ priority, hovered }: { priority: number; hovered: boolean }) {
  const fillLevel = priority === 1 ? 1 : priority === 2 ? 0.55 : 0.15;

  return (
    <svg viewBox="0 0 20 28" className="w-4 h-6 shrink-0" fill="none">
      <path
        d="M2 1h16v24l-8-6-8 6z"
        stroke="#D4A574"
        strokeWidth="1.1"
        fill="#D4A574"
        fillOpacity={hovered ? fillLevel * 0.85 : fillLevel * 0.55}
        style={{ transition: "fill-opacity 0.3s ease-out" }}
      />
      {hovered && (
        <path
          d="M2 1h16v24l-8-6-8 6z"
          stroke="#F5F0E8"
          strokeWidth="0.6"
          strokeOpacity="0.4"
          fill="none"
        />
      )}
    </svg>
  );
}
"use client";

type Category = "mathematics" | "physics" | "chemistry" | "history" | "literature" | "biology" | "technology" | "general";

const CATEGORY_KEYWORDS: Record<Category, string[]> = {
  mathematics: ["math", "algebra", "calculus", "geometry", "statistics", "linear"],
  physics: ["physics", "mechanics", "thermodynamics", "quantum", "relativity", "astronomy"],
  chemistry: ["chemistry", "chemical", "organic", "molecule", "reaction", "inorganic"],
  history: ["history", "polity", "civics", "politics", "government", "ancient", "civilization"],
  literature: ["literature", "english", "writing", "poetry", "language", "grammar"],
  biology: ["biology", "anatomy", "genetics", "ecology", "botany", "zoology", "environmental studies"],
  technology: ["computer science", "ai", "deep learning", "dsa", "web development", "engineering"],
  general: [],
};

export function detectCategory(subjectName: string): Category {
  const lower = subjectName.toLowerCase();
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) return category as Category;
  }
  return "general";
}

// ── Small crest icon (used on the card itself, ~32px) ──────────────

export function SubjectCrestIcon({ category, className = "w-8 h-8" }: { category: Category; className?: string }) {
  const stroke = "#D4A574";
  const fill = "none";

  switch (category) {
    case "mathematics":
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <path d="M8 7h16l-7 9 7 9H8l7-9z" stroke={stroke} strokeWidth="1.3" strokeLinejoin="round" />
          <circle cx="16" cy="16" r="14" stroke={stroke} strokeWidth="0.6" strokeOpacity="0.4" />
        </svg>
      );
    case "physics":
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <circle cx="16" cy="16" r="3" fill={stroke} />
          <ellipse cx="16" cy="16" rx="13" ry="5" stroke={stroke} strokeWidth="1.1" />
          <ellipse cx="16" cy="16" rx="13" ry="5" stroke={stroke} strokeWidth="1.1" transform="rotate(60 16 16)" />
          <ellipse cx="16" cy="16" rx="13" ry="5" stroke={stroke} strokeWidth="1.1" transform="rotate(120 16 16)" />
        </svg>
      );
    case "chemistry":
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <circle cx="10" cy="10" r="2.5" stroke={stroke} strokeWidth="1.2" />
          <circle cx="22" cy="10" r="2.5" stroke={stroke} strokeWidth="1.2" />
          <circle cx="16" cy="20" r="2.5" stroke={stroke} strokeWidth="1.2" />
          <circle cx="16" cy="9" r="1.8" stroke={stroke} strokeWidth="1.2" />
          <path d="M12 11l3-1M20 11l-3-1M17 12l-1 6M15 12l1 6" stroke={stroke} strokeWidth="1" />
        </svg>
      );
    case "history":
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <path d="M6 12h20M8 12v12M12 12v12M16 12v12M20 12v12M24 12v12M5 24h22M16 4l9 6H7z" stroke={stroke} strokeWidth="1.2" strokeLinejoin="round" />
        </svg>
      );
    case "literature":
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <path d="M9 25C9 14 15 7 24 6c0 9-6 16-15 19z" stroke={stroke} strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M9 25l13-15" stroke={stroke} strokeWidth="1" />
        </svg>
      );
    case "biology":
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <path d="M16 27V11M16 11c0-5 4-7 8-7-1 5-3 8-8 8zM16 16c0-4-4-6-8-6 1 4 3 6 8 6z" stroke={stroke} strokeWidth="1.2" strokeLinejoin="round" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 32 32" className={className} fill={fill}>
          <circle cx="16" cy="16" r="3.2" fill={stroke} />
          <circle cx="7" cy="9" r="1.6" stroke={stroke} strokeWidth="1.1" />
          <circle cx="25" cy="9" r="1.6" stroke={stroke} strokeWidth="1.1" />
          <circle cx="16" cy="25" r="1.6" stroke={stroke} strokeWidth="1.1" />
          <path d="M16 16L7 9M16 16l9-7M16 16v9" stroke={stroke} strokeWidth="1" />
        </svg>
      );
  }
}

// ── Oversized background watermark (opacity 0.03-0.05, sits behind content) ──

const WATERMARK_GLYPH: Record<Category, string> = {
  mathematics: "Σ",
  physics: "☉",
  chemistry: "⌬",
  history: "🏛️",
  literature: "✒",
  biology: "🌱",
  technology: "</>",
  general: "☕︎",
};

export function SubjectWatermark({ category }: { category: Category }) {
  return (
    <div
      className="absolute -right-4 -bottom-6 pointer-events-none select-none font-display"
      style={{ fontSize: 130, color: "#D4A574", opacity: 0.045, lineHeight: 1 }}
      aria-hidden
    >
      {WATERMARK_GLYPH[category]}
    </div>
  );
}
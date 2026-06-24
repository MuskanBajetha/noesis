"use client";

export function QuillIcon({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className="w-7 h-7" fill="none">
      {/* Feather Body */}
      <path
        d="M24 6C19 6 13.5 10 11.5 15.5C10.5 18 10 20.5 9 22C11 21 14 20 16.5 18.5M19.5 15.5C21.5 14 23 11.5 24 6ZM9 22L6 25"
        stroke="#7FA3B8" 
        strokeWidth="1.2" 
        strokeLinecap="round"
        strokeLinejoin="round"
        className={active ? "transition-all duration-700" : ""}
        style={{ filter: active ? "drop-shadow(0 0 4px rgba(212,165,116,0.5))" : "none" }}
      />
      {/* Animated Ink/Glow Tip */}
      <circle cx="9" cy="22" r="1.3" fill="#7FA3B8" opacity={active ? 0.9 : 0.4}>
        {active && <animate attributeName="opacity" values="0.9;0.3;0.9" dur="2s" repeatCount="indefinite" />}
      </circle>
    </svg>
  );
}


export function MasteryIcon({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className="w-7 h-7" fill="none">
      {/* Mortarboard Cap & Tassel */}
      <path
        d="M16 6L27 11L16 16L5 11L16 6ZM10 14.5V20.5C10 23.5 13 25 16 25C19 25 22 23.5 22 20.5V14.5M24.5 12.5V19.5"
        stroke="#7FA3B8" 
        strokeWidth="1.2" 
        strokeLinecap="round"
        strokeLinejoin="round"
        className={active ? "transition-all duration-700" : ""}
        style={{ filter: active ? "drop-shadow(0 0 4px rgba(212,165,116,0.5))" : "none" }}
      />
      {/* Animated Tassel Knot / Glow Point */}
      <circle cx="24.5" cy="20.5" r="1.3" fill="#7FA3B8" opacity={active ? 0.9 : 0.4}>
        {active && <animate attributeName="opacity" values="0.9;0.3;0.9" dur="2s" repeatCount="indefinite" />}
      </circle>
    </svg>
  );
}



export function NetworkNodeIcon({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className="w-7 h-7" fill="none">
      <circle cx="9" cy="10" r="2.2" fill="#7FA3B8" opacity={active ? 1 : 0.5} />
      <circle cx="23" cy="10" r="2.2" fill="#7FA3B8" opacity={active ? 1 : 0.5} />
      <circle cx="16" cy="22" r="2.2" fill="#7FA3B8" opacity={active ? 1 : 0.5} />
      <path
        d="M9 10L23 10M9 10L16 22M23 10L16 22"
        stroke="#7FA3B8" strokeWidth="1" strokeDasharray="3 2"
        opacity={active ? 0.8 : 0.3}
      >
        {active && <animate attributeName="stroke-dashoffset" values="0;10" dur="1.5s" repeatCount="indefinite" />}
      </path>
    </svg>
  );
}

export function ManuscriptIcon({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className="w-7 h-7" fill="none">
      <path d="M8 6h12l4 4v16H8z" stroke="#7FA3B8" strokeWidth="1.1" strokeLinejoin="round" />
      <path d="M20 6v4h4" stroke="#7FA3B8" strokeWidth="1" strokeLinejoin="round" />
      <path d="M11 14h10M11 18h10M11 22h6" stroke="#7FA3B8" strokeWidth="0.8" opacity={active ? 0.7 : 0.4} />
    </svg>
  );
}
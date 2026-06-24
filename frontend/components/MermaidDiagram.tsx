"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

let mermaidInitialized = false;

export default function MermaidDiagram({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  const idRef = useRef(`mermaid-${Math.random().toString(36).slice(2)}`);

  useEffect(() => {
    if (!mermaidInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        themeVariables: {
          background: "#18181b",
          primaryColor: "#27272a",
          primaryTextColor: "#F5F0E8",
          primaryBorderColor: "#8B7355",
          lineColor: "#52525b",
          secondaryColor: "#3f3f46",
          tertiaryColor: "#18181b",
        },
      });
      mermaidInitialized = true;
    }

    let cancelled = false;
    mermaid.render(idRef.current, code.trim())
      .then(({ svg }) => {
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => { cancelled = true; };
  }, [code]);

  if (error) return null; // fail silently — don't break the message if the diagram syntax is malformed

  return <div ref={ref} className="my-3 flex justify-center bg-card/50 rounded-lg p-3 overflow-x-auto" />;
}
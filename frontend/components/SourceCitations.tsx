"use client";

import { ExternalLink } from "lucide-react";

type Source = { title: string; url: string; snippet: string };

export default function SourceCitations({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-border/50 space-y-1.5">
      <p className="text-xs text-muted-foreground font-medium">Sources</p>
      {sources.map((s, i) => (
        <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="flex items-start gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors group">
          <span className="shrink-0">[{i + 1}]</span>
          <span className="truncate group-hover:underline">{s.title}</span>
          <ExternalLink className="w-3 h-3 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
        </a>
      ))}
    </div>
  );
}
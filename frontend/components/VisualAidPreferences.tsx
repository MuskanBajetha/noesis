"use client";

import { Network, LineChart, Image as ImageIcon, Video } from "lucide-react";
import { Button } from "@/components/ui/button";

type AidKey = "diagram" | "plot" | "image" | "video";

const AID_OPTIONS: { key: AidKey; label: string; icon: any; desc: string }[] = [
  { key: "diagram", label: "Diagrams", icon: Network, desc: "Flowcharts & concept maps" },
  { key: "plot", label: "Function plots", icon: LineChart, desc: "Math & physics graphs" },
  { key: "image", label: "Images", icon: ImageIcon, desc: "Real educational photos" },
  { key: "video", label: "Videos", icon: Video, desc: "Short explainer clips" },
];

export default function VisualAidPreferences({
  selected, onChange, onConfirm, compact
}: {
  selected: AidKey[];
  onChange: (aids: AidKey[]) => void;
  onConfirm?: () => void;
  compact?: boolean;
}) {
  const toggle = (key: AidKey) => {
    onChange(selected.includes(key) ? selected.filter((a) => a !== key) : [...selected, key]);
  };

  return (
    <div className={compact ? "space-y-2" : "space-y-3"}>
      {!compact && (
        <div>
          <p className="text-sm font-medium">Visual aids for this session</p>
          <p className="text-xs text-muted-foreground">Web search & citations are always included. Pick any additional aids you'd like.</p>
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        {AID_OPTIONS.map(({ key, label, icon: Icon, desc }) => {
          const active = selected.includes(key);
          return (
            <button
              key={key}
              onClick={() => toggle(key)}
              className={`flex items-start gap-2 p-2.5 rounded-lg border text-left transition-colors
                ${active ? "border-primary bg-primary/10" : "border-border hover:border-primary/40"}`}
            >
              <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`} />
              <div>
                <p className="text-xs font-medium">{label}</p>
                {!compact && <p className="text-xs text-muted-foreground">{desc}</p>}
              </div>
            </button>
          );
        })}
      </div>
      {onConfirm && (
        <Button size="sm" className="w-full" onClick={onConfirm}>Start session</Button>
      )}
    </div>
  );
}
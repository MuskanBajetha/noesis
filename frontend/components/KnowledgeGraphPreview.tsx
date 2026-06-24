"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type PreviewNode = { id: string; x: number; y: number; r: number; status: string };
type PreviewEdge = { x1: number; y1: number; x2: number; y2: number };

const STATUS_COLOR: Record<string, string> = {
  mastered: "#D4A574",
  learning: "#7FA3B8",
  struggling: "#B85C5C",
  unexplored: "#52525b",
};

export default function KnowledgeGraphPreview({ studentId }: { studentId: number | null }) {
  const router = useRouter();
  const [nodes, setNodes] = useState<PreviewNode[]>([]);
  const [edges, setEdges] = useState<PreviewEdge[]>([]);
  const [stats, setStats] = useState({ subjects: 0, topics: 0 });

  useEffect(() => {
    if (!studentId) return;
    api.get(`/knowledge-graph/${studentId}`).then((res) => {
      const allNodes = res.data.nodes || [];
      const allEdges = res.data.edges || [];

      setStats({
        subjects: allNodes.filter((n: any) => n.kind === "subject").length,
        topics: allNodes.filter((n: any) => n.kind === "topic").length,
      });

      // Lay out a SMALL sample (not the full graph) in a simple static
      // radial arrangement — this is a glance-preview, not a real layout.
      const sample = allNodes.slice(0, 14);
      const w = 280, h = 140;
      const cx = w / 2, cy = h / 2;

      const positioned: PreviewNode[] = sample.map((n: any, i: number) => {
        const angle = (i / sample.length) * Math.PI * 2;
        const radius = n.kind === "subject" ? 18 : 45 + (i % 3) * 12;
        return {
          id: n.id,
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius * 0.55,
          r: n.kind === "subject" ? 5 : 3,
          status: n.kind === "subject" ? "mastered" : n.status || "unexplored",
        };
      });
      setNodes(positioned);

      const idToPos: Record<string, PreviewNode> = {};
      positioned.forEach((p) => (idToPos[p.id] = p));

      const sampleIds = new Set(sample.map((n: any) => n.id));
      const positionedEdges: PreviewEdge[] = allEdges
        .filter((e: any) => sampleIds.has(e.source) && sampleIds.has(e.target))
        .slice(0, 16)
        .map((e: any) => {
          const a = idToPos[e.source];
          const b = idToPos[e.target];
          return a && b ? { x1: a.x, y1: a.y, x2: b.x, y2: b.y } : null;
        })
        .filter(Boolean) as PreviewEdge[];
      setEdges(positionedEdges);
    }).catch(() => {});
  }, [studentId]);

  return (
    <button
      onClick={() => router.push("/knowledge")}
      className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors p-4"
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-[#FFFFFF]/90 tracking-wide">Knowledge network</p>
        <span className="text-xs text-muted-foreground">{stats.subjects} subjects · {stats.topics} topics</span>
      </div>

      <svg viewBox="0 0 280 140" className="w-full h-28">
        {edges.map((e, i) => (
          <line
            key={i}
            x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
            stroke="#D4A574" strokeWidth="0.5" strokeOpacity="0.25"
            strokeDasharray="2 2"
          >
            <animate attributeName="stroke-opacity" values="0.15;0.4;0.15" dur={`${3 + i * 0.2}s`} repeatCount="indefinite" />
          </line>
        ))}
        {nodes.map((n, i) => (
          <circle key={n.id} cx={n.x} cy={n.y} r={n.r} fill={STATUS_COLOR[n.status] || "#52525b"} opacity="0.85">
            <animate
              attributeName="r"
              values={`${n.r};${n.r * 1.4};${n.r}`}
              dur={`${2.5 + (i % 4) * 0.4}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}
      </svg>

      <p className="text-xs text-muted-foreground mt-1 group-hover:text-[#FFFFFF]/70 transition-colors">
        View full graph →
      </p>
    </button>
  );
}
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useStudentId } from "@/hooks/useStudentId";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Brain, Loader2, Sparkles, Download } from "lucide-react";
import * as d3 from "d3";

type GraphNode = {
  id: string; name: string; kind: "subject" | "topic";
  mastery: number; status?: string; topic_count?: number; subject_id?: number;
};
type GraphEdge = { source: string; target: string; kind: "anchor" | "related" | "bridge"; description?: string; strength?: number };

export default function KnowledgePage() {
  const router = useRouter();
  const studentId = useStudentId();
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [stats, setStats] = useState({ subjects: 0, topics: 0, bridges: 0 });
  const [hoveredBridge, setHoveredBridge] = useState<GraphEdge | null>(null);

  useEffect(() => {
    if (!studentId) return;

    let latestNodes: GraphNode[] = [];
    let latestEdges: GraphEdge[] = [];

    api.get(`/knowledge-graph/${studentId}`)
      .then((res) => {
        latestNodes = res.data.nodes;
        latestEdges = res.data.edges;
        setStats({
          subjects: latestNodes.filter((n) => n.kind === "subject").length,
          topics: latestNodes.filter((n) => n.kind === "topic").length,
          bridges: latestEdges.filter((e) => e.kind === "bridge").length,
        });
        // Only render if container already has dimensions
        if (containerRef.current?.clientWidth) {
          renderGraph(latestNodes, latestEdges);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));

    // ResizeObserver renders graph once container gets real dimensions
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0 && latestNodes.length > 0) {
          renderGraph(latestNodes, latestEdges);
          observer.disconnect(); // render once, don't loop
        }
      }
    });

    if (containerRef.current) observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, [studentId]);

  const handleDiscoverBridges = async () => {
    if (!studentId) return;
    setDiscovering(true);
    try {
      await api.post(`/knowledge-bridges/${studentId}/discover`);
      const res = await api.get(`/knowledge-graph/${studentId}`);
      const nodes: GraphNode[] = res.data.nodes;
      const edges: GraphEdge[] = res.data.edges;
      setStats({
        subjects: nodes.filter((n) => n.kind === "subject").length,
        topics: nodes.filter((n) => n.kind === "topic").length,
        bridges: edges.filter((e) => e.kind === "bridge").length,
      });
      renderGraph(nodes, edges);
    } finally {
      setDiscovering(false);
    }
  };

  const exportSvg = (format: "svg" | "png" | "jpg") => {
    if (!svgRef.current) return;
    const svgEl = svgRef.current;
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgEl);

    if (format === "svg") {
      const blob = new Blob([svgString], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "knowledge-graph.svg"; a.click();
      URL.revokeObjectURL(url);
      return;
    }

    const img = new Image();
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const scale = 2;
      canvas.width = svgEl.clientWidth * scale;
      canvas.height = svgEl.clientHeight * scale;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.fillStyle = "#0A0E12";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0, svgEl.clientWidth, svgEl.clientHeight);
      URL.revokeObjectURL(url);

      const mime = format === "png" ? "image/png" : "image/jpeg";
      const a = document.createElement("a");
      a.href = canvas.toDataURL(mime, 0.95);
      a.download = `knowledge-graph.${format}`;
      a.click();
    };
    img.src = url;
  };

  const renderGraph = (nodes: GraphNode[], edges: GraphEdge[]) => {
    if (!svgRef.current || !containerRef.current || nodes.length === 0) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    d3.select(svgRef.current).selectAll("*").remove();

    const statusColor: Record<string, string> = {
      mastered: "#22c55e", learning: "#eab308", struggling: "#ef4444", unexplored: "#52525b",
    };

    const svg = d3.select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .style("cursor", "grab");

    // Subtle starfield particles in the background
    const particleLayer = svg.append("g");
    const particles = d3.range(80).map(() => ({
      x: Math.random() * width, y: Math.random() * height,
      r: Math.random() * 1.2 + 0.3, baseOpacity: Math.random() * 0.3 + 0.05,
    }));
    particleLayer.selectAll("circle").data(particles).join("circle")
      .attr("cx", (d) => d.x).attr("cy", (d) => d.y).attr("r", (d) => d.r)
      .attr("fill", "#8B7355").attr("opacity", (d) => d.baseOpacity);

    const container = svg.append("g");
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.25, 4])
      .on("zoom", (event) => container.attr("transform", event.transform));
    (svg as any).call(zoom);

    const simNodes = nodes.map((n) => ({
      ...n,
      x: width / 2 + (Math.random() - 0.5) * (n.kind === "subject" ? 250 : 500),
      y: height / 2 + (Math.random() - 0.5) * (n.kind === "subject" ? 180 : 420),
    }));

    const links = edges.map((e) => ({ ...e }));

    const simulation = d3.forceSimulation(simNodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id)
        .distance((l: any) => l.kind === "anchor" ? 95 : l.kind === "bridge" ? 220 : 165)
        .strength((l: any) => l.kind === "anchor" ? 0.8 : l.kind === "bridge" ? 0.15 : 0.3))
      .force("charge", d3.forceManyBody().strength((d: any) => d.kind === "subject" ? -700 : -140))
      .force("center", d3.forceCenter(width / 2, height / 2).strength(0.04))
      .force("collide", d3.forceCollide((d: any) => d.kind === "subject" ? 62 : 30))
      .force("bound-x", d3.forceX(width / 2).strength((d: any) => Math.abs((d.x || width/2) - width/2) > width * 0.46 ? 0.12 : 0.008))
      .force("bound-y", d3.forceY(height / 2).strength((d: any) => Math.abs((d.y || height/2) - height/2) > height * 0.46 ? 0.12 : 0.008))
      .alphaDecay(0.022)
      .velocityDecay(0.42);

    // Edges — anchors solid, related dashed-thin, bridges extra-thin/transparent with glow potential
    const linkGroup = container.append("g").selectAll("g.link-group").data(links).join("g").attr("class", "link-group");

    // Invisible wide hit area — this is what actually receives hover events
    const linkHit = linkGroup.append("line")
      .attr("stroke", "transparent")
      .attr("stroke-width", 14)
      .style("cursor", (d: any) => d.kind === "bridge" ? "pointer" : "default")
      .on("mouseenter", function (event, d: any) {
        if (d.kind !== "bridge") return;
        setHoveredBridge(d);
        d3.select(this.parentNode as any).select("line.visible-link")
          .attr("stroke-opacity", 0.9).attr("stroke-width", 2);
      })
      .on("mouseleave", function (event, d: any) {
        if (d.kind !== "bridge") return;
        setHoveredBridge(null);
        d3.select(this.parentNode as any).select("line.visible-link")
          .attr("stroke-opacity", 0.25 + (d.strength || 0.5) * 0.35).attr("stroke-width", 0.8);
      });

    // The actual thin visible line, purely cosmetic now — no event handlers needed
    const link = linkGroup.append("line")
      .attr("class", "visible-link")
      .attr("stroke", (d: any) =>
        d.kind === "bridge" ? "#8B7355" : d.kind === "anchor" ? "#3f3f46" : "#52525b")
      .attr("stroke-width", (d: any) => d.kind === "anchor" ? 1.4 : d.kind === "bridge" ? 0.8 : 1)
      .attr("stroke-opacity", (d: any) => d.kind === "bridge" ? (0.25 + (d.strength || 0.5) * 0.35) : d.kind === "anchor" ? 0.55 : 0.4)
      .attr("stroke-dasharray", (d: any) => d.kind === "bridge" ? "2 4" : d.kind === "related" ? "4 3" : "none")
      .style("pointer-events", "none");

    const node = container.append("g").selectAll("g").data(simNodes).join("g")
      .style("cursor", "pointer")
      .call(d3.drag<any, any>()
        .on("start", (event, d) => { if (!event.active) simulation.alphaTarget(0.25).restart(); d.fx = d.x; d.fy = d.y; svg.style("cursor", "grabbing"); })
        .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end", (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; svg.style("cursor", "grab"); }) as any
      );

    // Subject nodes — glowing ring via layered circles (no SVG filter, pure opacity stack)
    const subjectNode = node.filter((d: any) => d.kind === "subject");
    [56, 48].forEach((r, i) => {
      subjectNode.append("circle").attr("r", r).attr("fill", "none")
        .attr("stroke", "#8B7355").attr("stroke-width", i === 0 ? 0.5 : 1)
        .attr("stroke-opacity", i === 0 ? 0.2 : 0.4);
    });
    subjectNode.append("circle").attr("r", 40).attr("fill", "#18181b")
      .attr("stroke", "#8B7355").attr("stroke-width", 2.5);
    subjectNode.append("text").text((d: any) => d.name.length > 11 ? d.name.slice(0, 10) + "…" : d.name)
      .attr("text-anchor", "middle").attr("dy", 4).attr("font-size", 11).attr("font-weight", 700).attr("fill", "#F5F0E8");
    subjectNode.append("text").text((d: any) => `${d.topic_count} topics`)
      .attr("text-anchor", "middle").attr("dy", 18).attr("font-size", 8.5).attr("fill", "#8B7355");

    // Topic nodes — size scales with mastery tier
    const topicNode = node.filter((d: any) => d.kind === "topic");
    const tierRadius: Record<string, number> = { mastered: 22, learning: 18, struggling: 16, unexplored: 13 };
    topicNode.append("circle")
      .attr("r", (d: any) => tierRadius[d.status] || 14)
      .attr("fill", (d: any) => statusColor[d.status] || "#52525b")
      .attr("fill-opacity", 0.22)
      .attr("stroke", (d: any) => statusColor[d.status] || "#52525b")
      .attr("stroke-width", (d: any) => d.status === "mastered" ? 2 : 1.3);
    topicNode.append("text").text((d: any) => `${Math.round(d.mastery * 100)}%`)
      .attr("text-anchor", "middle").attr("dy", 3).attr("font-size", 9).attr("font-weight", 600).attr("fill", "#fafafa");
    topicNode.append("text").text((d: any) => d.name.length > 13 ? d.name.slice(0, 11) + "…" : d.name)
      .attr("text-anchor", "middle").attr("dy", 32).attr("font-size", 8.5).attr("fill", "#a1a1aa");

    // Hover a topic -> highlight its bridges + connected nodes, dim the rest
    node.on("mouseenter", function (event, d: any) {
      if (d.kind !== "topic") return;
      const connectedIds = new Set([d.id]);
      links.forEach((l: any) => {
        const s = typeof l.source === "object" ? l.source.id : l.source;
        const t = typeof l.target === "object" ? l.target.id : l.target;
        if (s === d.id) connectedIds.add(t);
        if (t === d.id) connectedIds.add(s);
      });
      node.attr("opacity", (n: any) => connectedIds.has(n.id) || n.kind === "subject" ? 1 : 0.25);
      link.attr("opacity", (l: any) => {
        const s = typeof l.source === "object" ? l.source.id : l.source;
        const t = typeof l.target === "object" ? l.target.id : l.target;
        return s === d.id || t === d.id ? 1 : 0.08;
      });
    }).on("mouseleave", function () {
      node.attr("opacity", 1);
      link.attr("opacity", 1);
    });

    simulation.on("tick", () => {
      linkHit.attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
      link.attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);

      // Gentle particle drift
      particleLayer.selectAll("circle").attr("cy", function (d: any) {
        d.y -= 0.05;
        if (d.y < 0) d.y = height;
        return d.y;
      });
    });

    simulation.on("end", () => {
      const allNodes = simNodes as any[];
      const xExtent = d3.extent(allNodes, (d) => d.x) as [number, number];
      const yExtent = d3.extent(allNodes, (d) => d.y) as [number, number];
      const graphW = xExtent[1] - xExtent[0] + 160;
      const graphH = yExtent[1] - yExtent[0] + 160;
      const scale = Math.min(1, Math.min(width / graphW, height / graphH));
      const tx = (width - scale * (xExtent[0] + xExtent[1])) / 2;
      const ty = (height - scale * (yExtent[0] + yExtent[1])) / 2;
      (svg as any).transition().duration(700).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
    });
  };

  return (
    <div className="fixed inset-0 bg-[#0A0E12] flex flex-col">
      {/* Floating header overlay */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-6 py-4 bg-gradient-to-b from-[#0A0E12] via-[#0A0E12]/80 to-transparent">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")} className="text-[#F5F0E8] hover:bg-white/10">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <Brain className="w-6 h-6 text-[#8B7355]" />
          <div>
            <h1 className="text-lg font-semibold text-[#F5F0E8]">Knowledge network</h1>
            <p className="text-xs text-[#F5F0E8]/50">
              {stats.subjects} subjects · {stats.topics} topics · {stats.bridges} bridges
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm" variant="outline"
            className="border-[#8B7355]/40 text-[#F5F0E8] hover:bg-[#8B7355]/10 hover:text-[#F5F0E8]"
            onClick={handleDiscoverBridges} disabled={discovering}
          >
            {discovering ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-1.5" />}
            Find bridges
          </Button>
          <Button size="sm" variant="outline" className="border-[#8B7355]/40 text-[#F5F0E8] hover:bg-[#8B7355]/10 hover:text-[#F5F0E8]" onClick={() => exportSvg("png")}>
            <Download className="w-3.5 h-3.5 mr-1.5" /> PNG
          </Button>
          <Button size="sm" variant="outline" className="border-[#8B7355]/40 text-[#F5F0E8] hover:bg-[#8B7355]/10 hover:text-[#F5F0E8]" onClick={() => exportSvg("jpg")}>
            JPG
          </Button>
          <Button size="sm" variant="outline" className="border-[#8B7355]/40 text-[#F5F0E8] hover:bg-[#8B7355]/10 hover:text-[#F5F0E8]" onClick={() => exportSvg("svg")}>
            SVG
          </Button>
        </div>
      </div>

      {/* Bridge tooltip on hover */}
      {hoveredBridge && (
        <div className="absolute bottom-6 left-6 z-10 max-w-md bg-[#18181b]/95 border border-[#8B7355]/40 rounded-lg px-4 py-3 backdrop-blur-sm">
          <p className="text-xs text-[#8B7355] font-medium mb-1">Knowledge bridge</p>
          <p className="text-sm text-[#F5F0E8]/80">{hoveredBridge.description}</p>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-6 right-6 z-10 flex flex-col gap-1.5 text-xs text-[#F5F0E8]/60">
        <span className="flex items-center gap-1.5 justify-end"><span className="w-2.5 h-2.5 rounded-full bg-green-500" /> Mastered</span>
        <span className="flex items-center gap-1.5 justify-end"><span className="w-2.5 h-2.5 rounded-full bg-yellow-500" /> Learning</span>
        <span className="flex items-center gap-1.5 justify-end"><span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Struggling</span>
        <span className="flex items-center gap-1.5 justify-end"><span className="w-2.5 h-2.5 rounded-full bg-zinc-600" /> Unexplored</span>
        <span className="flex items-center gap-1.5 justify-end"><span className="w-3 h-px bg-[#8B7355] opacity-50" style={{ borderTop: "1px dashed #8B7355" }} /> Bridge</span>
      </div>

      {/* Full viewport graph canvas */}
      <div ref={containerRef} className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-[#F5F0E8]/40" />
          </div>
        ) : stats.subjects === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-[#F5F0E8]/40 text-sm">
            No subjects yet — set one up from the dashboard first.
          </div>
        ) : (
          <svg ref={svgRef} className="w-full h-full" />
        )}
      </div>
    </div>
  );
}
"use client";

import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type PlotSpec =
  | { type: "function"; x: (number | null)[]; y: (number | null)[]; title: string; x_label: string; y_label: string }
  | { type: "scatter"; series: { name: string; x: number[]; y: number[] }[]; title: string; x_label: string; y_label: string };

export default function FunctionPlot({ spec }: { spec: PlotSpec }) {
  const layout = {
    title: { text: spec.title, font: { color: "#F5F0E8", size: 13 } },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#a1a1aa", size: 11 },
    xaxis: { title: spec.x_label, gridcolor: "#27272a", zerolinecolor: "#3f3f46" },
    yaxis: { title: spec.y_label, gridcolor: "#27272a", zerolinecolor: "#3f3f46" },
    margin: { t: 36, b: 40, l: 48, r: 16 },
    height: 280,
    showlegend: spec.type === "scatter",
    legend: { font: { color: "#a1a1aa", size: 10 } },
  };

  const data = spec.type === "function"
    ? [{ x: spec.x, y: spec.y, type: "scatter" as const, mode: "lines" as const, line: { color: "#8B7355", width: 2 } }]
    : spec.series.map((s) => ({ x: s.x, y: s.y, name: s.name, type: "scatter" as const, mode: "markers+lines" as const }));

  return (
    <div className="my-3 bg-card/50 rounded-lg p-2 overflow-x-auto">
      <Plot
        data={data}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
      />
    </div>
  );
}
"use client";

import { InlineMath, BlockMath } from "react-katex";
import "katex/dist/katex.min.css";
import MermaidDiagram from "./MermaidDiagram";
import FunctionPlot from "./FunctionPlot";
import RetrievedImage from "./RetrievedImage";
import VideoEmbed from "./VideoEmbed";

type Segment =
  | { type: "text"; content: string }
  | { type: "bold"; content: string }
  | { type: "inline-math"; content: string }
  | { type: "block-math"; content: string }
  | { type: "mermaid"; content: string }
  | { type: "plot"; content: string }
  | { type: "image"; content: string }
  | { type: "video"; content: string };

function parseTextChunk(text: string, segments: Segment[]) {
  const blockSplit = text.split(/(\$\$[^$]+\$\$)/g);
  for (const blockPart of blockSplit) {
    if (blockPart.startsWith("$$") && blockPart.endsWith("$$")) {
      segments.push({ type: "block-math", content: blockPart.slice(2, -2) });
      continue;
    }

    const inlineSplit = blockPart.split(/(\$[^$]+\$)/g);
    for (const inlinePart of inlineSplit) {
      if (inlinePart.startsWith("$") && inlinePart.endsWith("$") && inlinePart.length > 1) {
        segments.push({ type: "inline-math", content: inlinePart.slice(1, -1) });
        continue;
      }

      const boldSplit = inlinePart.split(/(\*\*[^*]+\*\*)/g);
      for (const boldPart of boldSplit) {
        if (boldPart.startsWith("**") && boldPart.endsWith("**")) {
          segments.push({ type: "bold", content: boldPart.slice(2, -2) });
        } else if (boldPart) {
          segments.push({ type: "text", content: boldPart });
        }
      }
    }
  }
}

function parseContent(raw: string): Segment[] {
  const segments: Segment[] = [];

  const mermaidSplit = raw.split(/```mermaid([\s\S]*?)```/g);

  mermaidSplit.forEach((chunk, idx) => {
    if (idx % 2 === 1) {
      segments.push({ type: "mermaid", content: chunk });
      return;
    }

    const plotSplit = chunk.split(/\[\[PLOT_(\d+)\]\]/g);
    plotSplit.forEach((plotPart, pIdx) => {
      if (pIdx % 2 === 1) {
        segments.push({ type: "plot", content: plotPart });
        return;
      }

      const imageSplit = plotPart.split(/\[\[IMAGE_(\d+)\]\]/g);
      imageSplit.forEach((imgPart, iIdx) => {
        if (iIdx % 2 === 1) {
          segments.push({ type: "image", content: imgPart });
          return;
        }

        const videoSplit = imgPart.split(/\[\[VIDEO_(\d+)\]\]/g);
        videoSplit.forEach((vidPart, vIdx) => {
          if (vIdx % 2 === 1) {
            segments.push({ type: "video", content: vidPart });
            return;
          }

          parseTextChunk(vidPart, segments);
        });
      });
    });
  });

  return segments;
}

export default function MessageContent({
  content, plots, images, videos
}: {
  content: string; plots?: any[]; images?: any[]; videos?: any[];
}) {
  const segments = parseContent(content);

  return (
    <>
      {segments.map((seg, i) => {
        switch (seg.type) {
          case "bold":
            return <strong key={i}>{seg.content}</strong>;
          case "mermaid":
            return <MermaidDiagram key={i} code={seg.content} />;
          case "plot": {
            const idx = parseInt(seg.content, 10);
            const spec = plots?.[idx];
            return spec ? <FunctionPlot key={i} spec={spec} /> : null;
          }
          case "image": {
            const idx = parseInt(seg.content, 10);
            const data = images?.[idx];
            return data ? <RetrievedImage key={i} data={data} /> : null;
          }
          case "video": {
            const idx = parseInt(seg.content, 10);
            const data = videos?.[idx];
            return data ? <VideoEmbed key={i} data={data} /> : null;
          }
          case "inline-math":
            try {
              return <InlineMath key={i} math={seg.content} />;
            } catch {
              return <span key={i}>{seg.content}</span>;
            }
          case "block-math":
            try {
              return (
                <div key={i} className="my-2 overflow-x-auto">
                  <BlockMath math={seg.content} />
                </div>
              );
            } catch {
              return <span key={i}>{seg.content}</span>;
            }
          default:
            return <span key={i}>{seg.content}</span>;
        }
      })}
    </>
  );
}
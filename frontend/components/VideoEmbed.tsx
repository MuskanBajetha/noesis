"use client";

import { useState } from "react";
import { Play } from "lucide-react";

type VideoData = {
  video_id: string; title: string; channel: string;
  thumbnail: string; url: string;
};

export default function VideoEmbed({ data }: { data: VideoData }) {
  const [playing, setPlaying] = useState(false);

  return (
    <div className="my-3 max-w-sm rounded-lg overflow-hidden border border-border bg-card/50">
      {playing ? (
        <div className="aspect-video">
          <iframe
            width="100%" height="100%"
            src={`https://www.youtube.com/embed/${data.video_id}?autoplay=1`}
            title={data.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      ) : (
        <button onClick={() => setPlaying(true)} className="relative w-full aspect-video group block">
          <img src={data.thumbnail} alt={data.title} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/30 group-hover:bg-black/40 transition-colors flex items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center">
              <Play className="w-5 h-5 text-black fill-black ml-0.5" />
            </div>
          </div>
        </button>
      )}
      <div className="p-2.5">
        <p className="text-xs font-medium line-clamp-2">{data.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{data.channel}</p>
      </div>
    </div>
  );
}
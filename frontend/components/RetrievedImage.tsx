"use client";

type ImageData = {
  url: string; title: string; source_page: string;
  license: string; attribution: string;
};

export default function RetrievedImage({ data }: { data: ImageData }) {
  return (
    <figure className="my-3 max-w-sm">
      <a href={data.source_page} target="_blank" rel="noopener noreferrer">
        <img
          src={data.url}
          alt={data.title}
          className="rounded-lg border border-border w-full"
          loading="lazy"
        />
      </a>
      <figcaption className="text-xs text-muted-foreground mt-1.5 leading-snug">
        {data.title} · {data.attribution} · {data.license}
      </figcaption>
    </figure>
  );
}
import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search_trusted_sources(query: str, topic_name: str, max_results: int = 3) -> list[dict]:
    """
    Searches the web for trusted, citable sources on a topic. Used to ground
    full explanations — especially important for prebuilt domains with no
    uploaded material, where this becomes the ONLY external grounding source.
    """
    try:
        response = tavily_client.search(
            query=f"{topic_name}: {query}",
            search_depth="basic",
            max_results=max_results,
            include_domains=[],  # left open; Tavily already biases toward reputable sources
        )
        results = response.get("results", [])

        return [
            {
                "title": r.get("title", "")[:120],
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:400],
            }
            for r in results if r.get("url")
        ]
    except Exception:
        return []


def format_sources_for_prompt(sources: list[dict]) -> str:
    """Formats search results as grounding context for the explanation prompt."""
    if not sources:
        return ""
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(f"[Source {i}: {s['title']}]\n{s['snippet']}")
    return "\n\n".join(parts)
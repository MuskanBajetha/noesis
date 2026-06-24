import requests

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

def _try_search(query: str, headers: dict) -> dict | None:
    """Single search attempt against Wikimedia for one query string."""
    # print(f"[IMAGE DEBUG] Trying query: '{query}'")
    try:
        search_resp = requests.get(WIKIMEDIA_API, params={
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{query} filetype:bitmap",
            "srnamespace": 6,
            "srlimit": 5,
        }, headers=headers, timeout=6)
        search_resp.raise_for_status()
        results = search_resp.json().get("query", {}).get("search", [])
        # print(f"[IMAGE DEBUG] '{query}' returned {len(results)} results")

        if not results:
            return None

        for result in results:
            title = result["title"]

            info_resp = requests.get(WIKIMEDIA_API, params={
                "action": "query", "format": "json",
                "titles": title, "prop": "imageinfo",
                "iiprop": "url|extmetadata", "iiurlwidth": 600,
            }, headers=headers, timeout=6)
            info_resp.raise_for_status()
            pages = info_resp.json().get("query", {}).get("pages", {})

            for page in pages.values():
                imageinfo = page.get("imageinfo")
                if not imageinfo:
                    continue
                info = imageinfo[0]
                url = info.get("thumburl") or info.get("url")
                if not url:
                    continue

                extmeta = info.get("extmetadata", {})
                artist = extmeta.get("Artist", {}).get("value", "")
                license_name = extmeta.get("LicenseShortName", {}).get("value", "")

                # print(f"[IMAGE DEBUG] SUCCESS with query '{query}' — found: {url}")
                return {
                    "url": url,
                    "title": title.replace("File:", ""),
                    "source_page": f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}",
                    "license": license_name or "See Wikimedia Commons",
                    "attribution": _strip_html(artist) if artist else "Wikimedia Commons",
                }
        return None
    except requests.RequestException as e:
        # print(f"[IMAGE DEBUG] RequestException for '{query}': {e}")
        return None


def search_educational_image(query: str) -> dict | None:
    """
    Searches Wikimedia Commons for an educational image, with automatic
    fallback to a progressively broader query if the first (specific) attempt
    finds nothing — Wikimedia's search is literal keyword matching, so an
    overly specific query often returns zero results even when a perfectly
    good, more general match exists.
    """
    headers = {
        "User-Agent": "Noesis-EdTech-Tutor/1.0 (https://noesis.example.com; educational-use) Python-requests"
    }


    # Attempt 1: the query as given
    result = _try_search(query, headers)
    if result:
        return result

    # Attempt 2: broaden by dropping to just the first 2 words — usually
    # the core subject (e.g. "Isaac Newton portrait painting" -> "Isaac Newton")
    words = query.split()
    if len(words) > 2:
        broadened = " ".join(words[:2])
        result = _try_search(broadened, headers)
        if result:
            return result

    # Attempt 3: just the single most important word (usually the proper noun)
    if len(words) > 1:
        result = _try_search(words[0], headers)
        if result:
            return result

    # print(f"[IMAGE DEBUG] All attempts exhausted for original query: '{query}'")
    return None


def _strip_html(text: str) -> str:
    """Wikimedia's extmetadata often contains raw HTML in attribution fields."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()

import re
import json


def extract_image_blocks(text: str) -> tuple[str, list[dict]]:
    images = []
    pattern = re.compile(r"```image\s*([\s\S]*?)```")
    # print(f"[IMAGE DEBUG] extract_image_blocks scanning text, contains '```image': {'```image' in text}")

    def replace(match):
        raw = match.group(1).strip()
        # print(f"[IMAGE DEBUG] Found image block, raw content: {raw}")
        try:
            spec = json.loads(raw)
            query = spec.get("query", "").strip()
        except Exception as e:
            # print(f"[IMAGE DEBUG] Failed to parse JSON: {e}")
            return ""

        if not query:
            return ""

        result = search_educational_image(query)
        if not result:
            return ""  # no match found — silently drop rather than show a broken block

        images.append(result)
        return f"\n[[IMAGE_{len(images) - 1}]]\n"

    cleaned_text = pattern.sub(replace, text)
    return cleaned_text, images


import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from app.schemas.eventSchema import EventCreate, WebIngestionRequest
from app.services.event_service import upsert_events

DEFAULT_EVENT_QUERY = "upcoming cultural entertainment science political local events Hyderabad"
REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = "getAHintService/1.0 event-ingestion"


def ingest_web_events(db: Session, request: WebIngestionRequest) -> Dict[str, Any]:
    urls = _discover_urls(request)
    extracted_events: List[EventCreate] = []
    failed_urls = []

    for url in urls:
        try:
            html = _fetch_url(url)
            extracted_events.extend(_extract_events_from_html(html, url))
        except Exception as e:
            failed_urls.append({"url": url, "error": str(e)})

    deduped_events = _dedupe_events(extracted_events)
    ingestion_result = upsert_events(db, deduped_events, update_embeddings=request.train_model)

    return {
        "searched_queries": _queries_for_request(request),
        "urls_checked": len(urls),
        "events_extracted": len(extracted_events),
        "events_after_dedupe": len(deduped_events),
        "ingestion": ingestion_result,
        "failed_urls": failed_urls,
        "embedding_update": "per_event" if request.train_model else "skipped",
    }


def _discover_urls(request: WebIngestionRequest) -> List[str]:
    urls = list(request.source_urls or [])
    configured_urls = os.getenv("EVENT_SOURCE_URLS", "").strip()
    if configured_urls:
        urls.extend(url.strip() for url in configured_urls.split(",") if url.strip())

    for query in _queries_for_request(request):
        urls.extend(_search_web(query, request.max_search_results))

    return _dedupe_urls(urls)


def _queries_for_request(request: WebIngestionRequest) -> List[str]:
    queries = request.queries or []
    if not queries and not request.source_urls and not os.getenv("EVENT_SOURCE_URLS"):
        queries = [DEFAULT_EVENT_QUERY]

    return [query if request.city.lower() in query.lower() else f"{query} {request.city}" for query in queries]


def _search_web(query: str, max_results: int) -> List[str]:
    serper_api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not serper_api_key:
        return []

    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": serper_api_key, "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    urls = []
    for result in payload.get("organic", []):
        link = result.get("link")
        if link:
            urls.append(link)
    return urls


def _fetch_url(url: str) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text


def _extract_events_from_html(html: str, source_url: str) -> List[EventCreate]:
    json_ld_events = []
    for json_ld in _extract_json_ld_blocks(html):
        json_ld_events.extend(_events_from_json_ld(json_ld, source_url))

    if json_ld_events:
        return json_ld_events

    fallback_event = _fallback_event_from_html(html, source_url)
    return [fallback_event] if fallback_event else []


def _extract_json_ld_blocks(html: str) -> Iterable[Any]:
    pattern = re.compile(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html):
        raw_json = _strip_html_comments(match.group(1)).strip()
        if not raw_json:
            continue
        try:
            yield json.loads(raw_json)
        except json.JSONDecodeError:
            continue


def _strip_html_comments(value: str) -> str:
    return re.sub(r"^\s*<!--|-->\s*$", "", value.strip())


def _events_from_json_ld(data: Any, source_url: str) -> List[EventCreate]:
    events = []
    for node in _walk_json_ld(data):
        node_type = node.get("@type")
        node_types = node_type if isinstance(node_type, list) else [node_type]
        if "Event" not in node_types:
            continue

        event = _event_from_json_ld_node(node, source_url)
        if event:
            events.append(event)
    return events


def _walk_json_ld(data: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(data, dict):
        yield data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _walk_json_ld(item)
    elif isinstance(data, list):
        for item in data:
            yield from _walk_json_ld(item)


def _event_from_json_ld_node(node: Dict[str, Any], source_url: str) -> EventCreate | None:
    name = _clean_text(node.get("name"))
    start_date = _normalize_event_date(node.get("startDate") or node.get("start_date"))
    if not name or not start_date:
        return None

    description = _clean_text(node.get("description")) or name
    address = _location_to_text(node.get("location")) or _domain_name(source_url)

    return EventCreate(
        event_name=name,
        event_description=description,
        event_date=start_date,
        event_address=address,
        source_name=source_url,
        source_type="web_json_ld",
    )


def _fallback_event_from_html(html: str, source_url: str) -> EventCreate | None:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = _clean_text(_strip_tags(title_match.group(1))) if title_match else ""
    date_text = _find_date_in_text(_strip_tags(html))

    if not title or not date_text:
        return None

    return EventCreate(
        event_name=title[:255],
        event_description=f"Event listing discovered from {source_url}",
        event_date=date_text,
        event_address=_domain_name(source_url),
        source_name=source_url,
        source_type="web_fallback",
    )


def _location_to_text(location: Any) -> str:
    if isinstance(location, str):
        return _clean_text(location)
    if not isinstance(location, dict):
        return ""

    name = _clean_text(location.get("name"))
    address = location.get("address")
    if isinstance(address, dict):
        address_parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("postalCode"),
            address.get("addressCountry"),
        ]
        address_text = ", ".join(_clean_text(part) for part in address_parts if _clean_text(part))
    else:
        address_text = _clean_text(address)

    return ", ".join(part for part in (name, address_text) if part)


def _normalize_event_date(value: Any) -> str:
    if not value:
        return ""

    date_text = str(value).strip()
    if "T" in date_text:
        date_text = date_text.split("T", 1)[0]

    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_text, date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)
    return match.group(0) if match else date_text


def _find_date_in_text(text: str) -> str:
    patterns = (
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _normalize_event_date(match.group(0))
    return ""


def _dedupe_events(events: List[EventCreate]) -> List[EventCreate]:
    seen = set()
    deduped = []
    for event in events:
        key = (
            event.event_name.strip().lower(),
            event.event_date.strip(),
            event.event_address.strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def _dedupe_urls(urls: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for url in urls:
        normalized = url.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _domain_name(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url

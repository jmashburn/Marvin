"""RSS/Atom feed — a source integration that emits an event per new item.

``poll()`` fetches and parses the feed and returns one PolledEvent per item, keyed by a stable dedup
id (guid/link). The core calls poll() on a cadence and dispatches the returned events; this provider
is stateless by design.
"""

from xml.etree import ElementTree

from marvin_integration_sdk import (
    CATEGORY_SOURCE,
    IntegrationContext,
    IntegrationProvider,
    PolledEvent,
    ProviderEvent,
    register_provider,
)

_MAX_ITEMS = 50
# Atom uses a namespace; RSS 2.0 does not. Handle both by checking local/namespaced tag names.
_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_items(raw: bytes) -> list[dict]:
    """Return [{title, link, guid}] for both RSS 2.0 <item> and Atom <entry>."""
    root = ElementTree.fromstring(raw)
    items: list[dict] = []

    # RSS 2.0: channel/item
    for item in root.iter("item"):
        link = _text(item.find("link"))
        guid = _text(item.find("guid")) or link
        items.append({"title": _text(item.find("title")), "link": link, "guid": guid})
        if len(items) >= _MAX_ITEMS:
            return items

    # Atom: entry with namespaced tags
    if not items:
        for entry in root.iter(f"{_ATOM_NS}entry"):
            link_el = entry.find(f"{_ATOM_NS}link")
            link = link_el.get("href", "") if link_el is not None else ""
            guid = _text(entry.find(f"{_ATOM_NS}id")) or link
            items.append({"title": _text(entry.find(f"{_ATOM_NS}title")), "link": link, "guid": guid})
            if len(items) >= _MAX_ITEMS:
                break

    return items


@register_provider
class RssProvider(IntegrationProvider):
    slug = "rss"
    name = "RSS / Atom Feed"
    description = "Emit an event for each item in an external RSS or Atom feed."
    category = CATEGORY_SOURCE

    config_schema = {
        "type": "object",
        "properties": {
            "feed_url": {"type": "string", "format": "uri", "title": "Feed URL"},
        },
        "required": ["feed_url"],
        "additionalProperties": False,
    }
    emits = (
        ProviderEvent(
            key="rss.item_published",
            label="Feed item published",
            description="A new item appeared in the feed.",
        ),
    )

    def check(self, ctx: IntegrationContext) -> tuple[str, str | None]:
        feed_url = (ctx.config or {}).get("feed_url")
        if not feed_url:
            return ("unconfigured", "Missing feed URL.")
        try:
            _parse_items(ctx.http.get(feed_url).content)
            return ("ok", None)
        except Exception as e:  # noqa: BLE001 — network + parse errors both mean "can't read feed"
            return ("error", f"Could not read feed: {e}")

    def poll(self, ctx: IntegrationContext) -> list[PolledEvent]:
        feed_url = (ctx.config or {}).get("feed_url")
        if not feed_url:
            return []
        try:
            items = _parse_items(ctx.http.get(feed_url).content)
        except Exception as e:  # noqa: BLE001 — a bad fetch/parse just yields no events this round
            ctx.logger.warning(f"[rss] poll failed for {feed_url}: {e}")
            return []

        return [
            PolledEvent(event_key="rss.item_published", dedup_key=item["guid"], message=item["title"], payload=item)
            for item in items
            if item["guid"]
        ]

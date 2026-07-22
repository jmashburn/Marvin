"""Unit tests for the integration provider registry (services/integrations).

Covers registry mechanics, the info() projection contract the /providers catalog relies on,
the built-in providers' check() logic, and offline RSS parsing — without a DB or network.
"""

import logging

import pytest

from marvin.services.integrations import (
    INTEGRATION_REGISTRY,
    IntegrationContext,
    get_provider,
    list_providers,
)
from marvin.services.integrations.providers.rss import _parse_items

_LOG = logging.getLogger("test")


class _StubHttp:
    """A no-op http helper; the check() paths under test don't perform requests."""

    def get(self, url, *, headers=None, timeout=15):  # pragma: no cover - not exercised here
        raise AssertionError("network not expected in these tests")

    def post(self, url, *, json=None, data=None, headers=None, timeout=15):  # pragma: no cover
        raise AssertionError("network not expected in these tests")


def _ctx(slug: str, *, secret=None, config=None) -> IntegrationContext:
    """A narrowed context — providers get only config/secret/logger/http."""
    return IntegrationContext(config=config or {}, secret=secret, logger=_LOG, http=_StubHttp())


def test_builtin_providers_are_registered():
    slugs = {p.slug for p in list_providers()}
    assert {"rss", "vercel_deploy"} <= slugs


def test_get_provider_roundtrip_and_unknown_raises():
    assert get_provider("rss").slug == "rss"
    with pytest.raises(KeyError):
        get_provider("does_not_exist")


def test_info_shape_matches_catalog_contract():
    info = get_provider("vercel_deploy").info()
    # The /providers catalog + frontend cards depend on exactly these keys.
    assert set(info) >= {"slug", "name", "category", "config_schema", "credentials", "emits", "actions"}
    assert info["category"] == "destination"
    assert any(c["key"] == "hook_url" for c in info["credentials"])
    assert any(a["key"] == "trigger_deploy" for a in info["actions"])


def test_vercel_check_logic():
    v = get_provider("vercel_deploy")
    assert v.check(_ctx("v", secret="https://api.vercel.com/hook/xyz")) == ("ok", None)
    assert v.check(_ctx("v", secret=None))[0] == "unconfigured"
    assert v.check(_ctx("v", secret="http://insecure"))[0] == "error"


def test_vercel_unknown_action_raises():
    v = get_provider("vercel_deploy")
    assert v.get_action("trigger_deploy") is not None
    assert v.get_action("nope") is None
    with pytest.raises(NotImplementedError):
        v.run_action("nope", {}, _ctx("v", secret="https://x"))


def test_rss_check_requires_feed_url():
    r = get_provider("rss")
    assert r.check(_ctx("r", config={}))[0] == "unconfigured"


def test_rss_parses_rss2_items():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <title>Feed</title>
      <item><title>First</title><link>https://ex.com/1</link><guid>g1</guid></item>
      <item><title>Second</title><link>https://ex.com/2</link></item>
    </channel></rss>"""
    items = _parse_items(xml)
    assert [i["title"] for i in items] == ["First", "Second"]
    assert items[0]["guid"] == "g1"
    # No <guid> → falls back to link, so dedup still has a stable key.
    assert items[1]["guid"] == "https://ex.com/2"


def test_rss_parses_atom_entries():
    xml = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Feed</title>
      <entry><title>Post</title><id>urn:1</id>
        <link href="https://ex.com/p1"/></entry>
    </feed>"""
    items = _parse_items(xml)
    assert len(items) == 1
    assert items[0]["title"] == "Post"
    assert items[0]["guid"] == "urn:1"
    assert items[0]["link"] == "https://ex.com/p1"


def test_registry_is_shared_singleton():
    # register_provider populates the same dict list_providers reads.
    assert INTEGRATION_REGISTRY["rss"] is get_provider("rss")

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


def test_load_reports_include_builtins():
    from marvin.services.integrations import load_reports

    reports = load_reports()
    builtins = [r for r in reports if r.source == "builtin"]
    assert builtins and builtins[0].ok
    assert {"rss", "vercel_deploy"} <= set(builtins[0].slugs)


def test_orphaned_row_reads_as_unavailable():
    # A row whose provider package isn't installed must surface as unavailable, not a stale status.
    import uuid
    from types import SimpleNamespace

    from marvin.routes.groups.integrations_controller import _to_read

    row = SimpleNamespace(
        id=uuid.uuid4(), provider="ghost_provider", name="Ghost", slug="ghost", enabled=True,
        config=None, secret_ref=None, status="ok", last_checked_at=None, last_error=None,
    )
    read = _to_read(row)
    assert read.status == "unavailable"
    assert "not installed" in (read.last_error or "")


def test_entry_point_discovery_is_resilient(monkeypatch):
    # A good plugin registers (with its distribution version); a broken one is reported failed and
    # skipped — it must not take down discovery of the others.
    from marvin_integration_sdk import INTEGRATION_REGISTRY, IntegrationProvider

    import marvin.services.integrations.loader as loader

    class _GoodProvider(IntegrationProvider):
        slug = "test_good"
        name = "Test Good"

    def _boom():
        raise RuntimeError("boom")

    class _EP:
        def __init__(self, name, fn, dist):
            self.name, self._fn, self.dist = name, fn, dist

        def load(self):
            return self._fn()

    class _Dist:
        def __init__(self, name, version):
            self.name, self.version = name, version

    eps = [
        _EP("good", lambda: _GoodProvider, _Dist("marvin-integration-good", "1.2.3")),
        _EP("bad", _boom, _Dist("marvin-integration-bad", "0.1")),
    ]
    monkeypatch.setattr(loader.importlib_metadata, "entry_points", lambda group=None: eps)
    try:
        reports = {r.name: r for r in loader._load_entry_points()}
        assert reports["good"].ok
        assert reports["good"].slugs == ["test_good"]
        assert reports["good"].version == "1.2.3"
        assert not reports["bad"].ok
        assert "boom" in (reports["bad"].error or "")
        assert "test_good" in INTEGRATION_REGISTRY
    finally:
        INTEGRATION_REGISTRY.pop("test_good", None)


def test_event_listener_runs_action_with_templated_args():
    # The core "consume integration via events" mechanism: a connected action fires when its event
    # does, with {{field}} placeholders filled from the event.
    import uuid

    from marvin_integration_sdk import INTEGRATION_REGISTRY, IntegrationProvider, ProviderAction, register_provider

    from marvin.services.event_bus_service.event_bus_listener import IntegrationEventListener

    calls: list = []

    class _RecorderProvider(IntegrationProvider):
        slug = "recorder"
        name = "Recorder"
        actions = (ProviderAction(key="do", label="Do"),)

        def run_action(self, key, args, ctx):
            calls.append((key, args))
            return {"ok": True}

    register_provider(_RecorderProvider)

    class _EvType:
        name = "entry-published"

    class _Event:
        event_type = _EvType()
        document_data = {"title": "Hello World", "slug": "hello"}
        entity_id = uuid.uuid4()
        entity_type = "entry"
        message = "published"

    try:
        listener = IntegrationEventListener(group_id=uuid.uuid4())
        sub = {
            "name": "My Slack", "provider": "recorder", "config": {}, "secret_ref": None,
            "action": "do", "args": {"text": "New: {{title}} ({{entity_type}})"},
        }
        listener.publish_to_subscribers(_Event(), [sub])
        assert calls == [("do", {"text": "New: Hello World (entry)"})]
    finally:
        INTEGRATION_REGISTRY.pop("recorder", None)


def test_event_listener_skips_uninstalled_provider():
    import uuid

    from marvin.services.event_bus_service.event_bus_listener import IntegrationEventListener

    class _EvType:
        name = "entry-published"

    class _Event:
        event_type = _EvType()
        document_data = {}
        entity_id = None
        entity_type = None
        message = ""

    listener = IntegrationEventListener(group_id=uuid.uuid4())
    # No exception even though provider isn't installed — just logged and skipped.
    listener.publish_to_subscribers(_Event(), [{"name": "Gone", "provider": "ghost", "config": {}, "secret_ref": None, "action": "x", "args": {}}])


def test_template_substitution():
    from marvin.services.event_bus_service.event_bus_listener import IntegrationEventListener

    out = IntegrationEventListener._template(
        {"text": "Hi {{name}}", "nested": {"k": "{{missing}}"}, "list": ["{{name}}"]},
        {"name": "Sam"},
    )
    assert out == {"text": "Hi Sam", "nested": {"k": "{{missing}}"}, "list": ["Sam"]}


def test_installed_provider_reads_normally():
    import uuid
    from types import SimpleNamespace

    from marvin.routes.groups.integrations_controller import _to_read

    row = SimpleNamespace(
        id=uuid.uuid4(), provider="rss", name="My feed", slug="my_feed", enabled=True,
        config={"feed_url": "https://x/feed"}, secret_ref=None, status="ok", last_checked_at=None, last_error=None,
    )
    read = _to_read(row)
    assert read.status == "ok"
    assert read.last_error is None

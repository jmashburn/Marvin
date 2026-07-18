"""Guard tests for the system workflow collection definitions.

These don't hit the DB — they assert the seeded definitions stay consistent with the entry
status vocabulary and the smart-rule evaluator, so a typo in a status can't ship a workflow
collection that silently matches nothing.
"""

from marvin.schemas.platform.entries import ENTRY_STATUSES
from marvin.services.collections.smart_collections import entry_matches_rules
from marvin.services.collections.system_collections import WORKFLOW_COLLECTIONS


def test_slugs_are_unique():
    slugs = [c["slug"] for c in WORKFLOW_COLLECTIONS]
    assert len(slugs) == len(set(slugs))


def test_every_rule_status_is_a_real_status():
    for c in WORKFLOW_COLLECTIONS:
        for status in c["statuses"]:
            assert status in ENTRY_STATUSES, f"{c['slug']} references unknown status {status!r}"


def test_expected_workflow_stages_present():
    slugs = {c["slug"] for c in WORKFLOW_COLLECTIONS}
    assert {"inbox", "drafts", "needs-review", "approved"} <= slugs


def test_rules_match_the_intended_status():
    """An entry with a stage's status matches that collection's rule and no other."""
    from types import SimpleNamespace

    for c in WORKFLOW_COLLECTIONS:
        rules = {"statuses": c["statuses"], "match": "all"}
        entry = SimpleNamespace(status=c["statuses"][0], entry_type=SimpleNamespace(slug="x"), tags=None)
        assert entry_matches_rules(entry, rules) is True
        # an entry in a different stage must not match
        other = next(o for o in WORKFLOW_COLLECTIONS if o["slug"] != c["slug"])
        other_entry = SimpleNamespace(status=other["statuses"][0], entry_type=SimpleNamespace(slug="x"), tags=None)
        assert entry_matches_rules(other_entry, rules) is False

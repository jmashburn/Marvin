"""Smart collections: rule-based, materialized membership.

A collection with ``is_smart=True`` carries ``smart_rules`` describing which entries belong to
it (by entry-type slug and/or status). Membership is **materialized** into ``EntryCollections``
rows — kept in sync by an event-bus reaction on entry lifecycle changes and re-evaluated when a
collection's rules change — so the read path (renderers-core, publishing) is unchanged: it reads
junction rows exactly as for a manually-curated collection.

Rule shape (every dimension optional; an absent/empty dimension is not constrained)::

    {
      "entry_types": ["bench-note", "article"],   # entry_type slugs
      "statuses": ["published"],                   # entry.status values
      "tags": ["leather", "waxed"],                # RESERVED — matches once entries carry tags
      "match": "all" | "any"                       # combine dimensions (default "all")
    }

An empty rule set matches **nothing** — so a misconfigured smart collection can't silently
swallow the whole workspace.

``tags`` is wired as a forward-compatible dimension: it reads ``entry.tags`` when present and
is simply inert until a tagging system lands. The plan is one shared tag vocabulary across
entries, assets, and resources, so the same rule dimension will generalize to smart collections
of any of those once tags exist.

MVP scope: a smart collection's membership is *fully* rule-derived (smart XOR manual) — these
helpers add/remove only to reflect the rules; manual pins on a smart collection are not
preserved. Mixed smart+manual collections are a later enhancement.

The sync helpers never commit — the caller owns the transaction.
"""

from marvin.core.root_logger import get_logger

logger = get_logger(__name__)


def entry_matches_rules(entry, rules: dict | None) -> bool:
    """Return True if ``entry`` satisfies a smart collection's ``rules``.

    ``entry`` may be an ORM ``Entries`` instance or any object exposing ``status`` and
    ``entry_type.slug``. An empty/None rule set matches nothing.
    """
    if not rules:
        return False

    dimensions: list[bool] = []

    entry_types = rules.get("entry_types")
    if entry_types:
        entry_type = getattr(entry, "entry_type", None)
        dimensions.append(getattr(entry_type, "slug", None) in entry_types)

    statuses = rules.get("statuses")
    if statuses:
        dimensions.append(getattr(entry, "status", None) in statuses)

    # Forward-compatible: inert until entries/assets/resources carry tags (shared vocabulary).
    tags = rules.get("tags")
    if tags:
        entry_tags = getattr(entry, "tags", None) or []
        dimensions.append(bool(set(tags) & set(entry_tags)))

    if not dimensions:
        return False

    if rules.get("match") == "any":
        return any(dimensions)
    return all(dimensions)


def _smart_collections(session, group_id):
    from marvin.db.models.platform.collections import Collections

    return session.query(Collections).filter_by(group_id=group_id, is_smart=True).all()


def sync_entry(session, group_id, entry) -> int:
    """Sync one entry's membership across every smart collection in its workspace.

    Adds the entry to smart collections whose rules it now matches and removes it from those it
    no longer matches. Returns the number of membership rows changed. Does not commit.
    """
    from marvin.db.models.platform.entry_collections import EntryCollections

    changed = 0
    for collection in _smart_collections(session, group_id):
        desired = entry_matches_rules(entry, collection.smart_rules)
        existing = (
            session.query(EntryCollections)
            .filter_by(entry_id=entry.id, collection_id=collection.id)
            .first()
        )
        if desired and existing is None:
            session.add(EntryCollections(entry_id=entry.id, collection_id=collection.id, sort_order=0))
            changed += 1
        elif not desired and existing is not None:
            session.delete(existing)
            changed += 1
    return changed


def sync_collection(session, group_id, collection) -> int:
    """Re-evaluate one smart collection's membership across all of the workspace's entries.

    Used when a collection's rules change and by the reconcile/backfill task. Returns the number
    of membership rows changed. Does not commit. A non-smart collection is left untouched.
    """
    if not getattr(collection, "is_smart", False):
        return 0

    from marvin.db.models.platform.entries import Entries
    from marvin.db.models.platform.entry_collections import EntryCollections

    rules = collection.smart_rules or {}
    entries = session.query(Entries).filter_by(group_id=group_id).all()
    desired = {e.id for e in entries if entry_matches_rules(e, rules)}
    current = {
        row.entry_id
        for row in session.query(EntryCollections).filter_by(collection_id=collection.id).all()
    }

    to_add = desired - current
    to_remove = current - desired
    for entry_id in to_add:
        session.add(EntryCollections(entry_id=entry_id, collection_id=collection.id, sort_order=0))
    if to_remove:
        session.query(EntryCollections).filter(
            EntryCollections.collection_id == collection.id,
            EntryCollections.entry_id.in_(to_remove),
        ).delete(synchronize_session=False)

    return len(to_add) + len(to_remove)

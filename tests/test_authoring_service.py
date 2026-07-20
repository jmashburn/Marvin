"""Tests for AuthoringService association helpers (the parts that don't need a live model).

Focus: _attach_existing_resources must resolve a resource by id, slug, OR name. The grounding block
lists resources by *name*, so the model returns names — slug-only resolution silently linked nothing
(a bug that affected both compose and revise).
"""

import uuid

from pytest import fixture

from marvin.db.models.platform import Entries, EntryResources, EntryTypes, Resources
from marvin.services.ai.authoring import AuthoringService


@fixture
def workspace(db_session):
    """A throwaway workspace with one entry + one resource ('Waxed Canvas' / 'waxed-canvas')."""
    from marvin.db.models.groups import Groups
    from marvin.db.models.users.users import Users

    gid = uuid.uuid4()
    marker = gid.hex[:8]
    g = Groups(session=db_session, name=f"auth-{marker}", slug=f"auth-{marker}")
    g.id = gid
    db_session.add(g)
    db_session.flush()

    uid = uuid.uuid4()
    db_session.execute(Users.__table__.insert().values(
        id=uid, group_id=gid, username=f"u-{marker}", email=f"u-{marker}@t.test",
        full_name="U", is_superuser=False, platform_role="NONE", auth_method="MARVIN",
    ))
    et = EntryTypes(session=db_session, group_id=gid, name="Note", slug="note", schema_json={})
    et.id = uuid.uuid4()
    db_session.add(et)
    db_session.flush()
    entry = Entries(session=db_session, group_id=gid, entry_type_id=et.id, title="T", slug=f"t-{marker}")
    db_session.add(entry)
    res = Resources(session=db_session, group_id=gid, name="Waxed Canvas", slug="waxed-canvas",
                    resource_type="material", created_by=uid)
    db_session.add(res)
    db_session.commit()

    yield gid, entry.id, res.id

    db_session.query(EntryResources).delete()
    db_session.query(Resources).filter(Resources.group_id == gid).delete()
    db_session.query(Entries).filter(Entries.group_id == gid).delete()
    db_session.query(EntryTypes).filter(EntryTypes.group_id == gid).delete()
    db_session.execute(Users.__table__.delete().where(Users.group_id == gid))
    db_session.query(Groups).filter(Groups.id == gid).delete()
    db_session.commit()


def _svc(db_session, gid):
    return AuthoringService(db_session, gid, user=None, provider=None, model=None)


def _count(db_session, entry_id, res_id):
    return db_session.query(EntryResources).filter_by(entry_id=entry_id, resource_id=res_id).count()


def test_attach_existing_resources_resolves_by_name(db_session, workspace):
    # THE regression: the model returns the resource NAME from the grounding, not the slug.
    gid, entry_id, res_id = workspace
    attached = _svc(db_session, gid)._attach_existing_resources(entry_id, ["Waxed Canvas"])
    db_session.commit()  # the caller (compose/revise) commits after
    assert attached == ["waxed-canvas"]
    assert _count(db_session, entry_id, res_id) == 1


def test_attach_existing_resources_resolves_by_slug_and_id(db_session, workspace):
    gid, entry_id, res_id = workspace
    svc = _svc(db_session, gid)
    assert svc._attach_existing_resources(entry_id, ["waxed-canvas"]) == ["waxed-canvas"]  # by slug
    db_session.commit()
    assert svc._attach_existing_resources(entry_id, [str(res_id)]) == []  # by id, already attached → no dup
    db_session.commit()
    assert _count(db_session, entry_id, res_id) == 1


def test_attach_existing_resources_ignores_unknown(db_session, workspace):
    gid, entry_id, res_id = workspace
    assert _svc(db_session, gid)._attach_existing_resources(entry_id, ["Does Not Exist", ""]) == []
    db_session.commit()
    assert _count(db_session, entry_id, res_id) == 0

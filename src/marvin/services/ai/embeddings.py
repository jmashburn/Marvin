"""
Embedding service — chunk text, embed via a provider, store, and search.

Vectors are stored as JSON float arrays in ai_embeddings (cross-DB), and cosine
similarity is computed in Python (numpy). This is O(n) over a workspace's chunks —
fine at hobby scale; migrate to pgvector on Postgres if it ever needs to scale.
"""

from pydantic import UUID4
from sqlalchemy.orm import Session

# Sensible default embedding model per provider (overridable by callers).
DEFAULT_EMBEDDING_MODELS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "azure": "text-embedding-3-small",
    "google": "models/text-embedding-004",
    "ollama": "nomic-embed-text",
}


_EMBEDDING_SETTING_KEYS: dict[str, str] = {
    "openai": "OPENAI_EMBEDDING_MODEL",
    "azure": "OPENAI_EMBEDDING_MODEL",
    "google": "GOOGLE_EMBEDDING_MODEL",
    "ollama": "OLLAMA_EMBEDDING_MODEL",
}


def default_embedding_model(provider_type: str) -> str | None:
    """Resolve the embedding model — AppSettings override first, then the built-in default."""
    from marvin.core.config import get_app_settings
    key = _EMBEDDING_SETTING_KEYS.get(provider_type)
    if key:
        configured = getattr(get_app_settings(), key, None)
        if configured:
            return configured
    return DEFAULT_EMBEDDING_MODELS.get(provider_type)


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 150) -> list[str]:
    """Split text into overlapping character windows. Simple and provider-agnostic."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    step = max(1, max_chars - overlap)
    while start < len(text):
        chunks.append(text[start:start + max_chars])
        start += step
    return chunks


def index_entity(
    session: Session,
    group_id: UUID4,
    entity_type: str,
    entity_id: UUID4,
    text: str,
    provider,
    model: str,
) -> int:
    """Chunk + embed `text` and (re)store the chunks for this entity+model. Returns chunk count."""
    from marvin.core.config import get_app_settings
    from marvin.db.models.groups.ai_embeddings import AIEmbeddingModel

    app = get_app_settings()
    chunks = chunk_text(
        text,
        max_chars=getattr(app, "AI_EMBED_CHUNK_SIZE", 1500),
        overlap=getattr(app, "AI_EMBED_CHUNK_OVERLAP", 150),
    )
    if not chunks:
        # No content — clear any stale embeddings for this entity+model.
        session.query(AIEmbeddingModel).filter_by(
            group_id=group_id, entity_type=entity_type, entity_id=entity_id, model_id=model
        ).delete()
        session.commit()
        return 0

    vectors = provider.embed(chunks, model)
    dims = len(vectors[0]) if vectors else 0

    session.query(AIEmbeddingModel).filter_by(
        group_id=group_id, entity_type=entity_type, entity_id=entity_id, model_id=model
    ).delete()
    for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=False)):
        session.add(AIEmbeddingModel(
            session=session,
            group_id=group_id,
            entity_type=entity_type,
            entity_id=entity_id,
            chunk_index=i,
            chunk_text=chunk,
            embedding=list(vec),
            model_id=model,
            dimensions=dims,
        ))
    session.commit()
    return len(chunks)


def _tags_line(obj) -> str | None:
    """A 'Tags: …' line (display names, human words) so tag vocabulary is semantically searchable."""
    tags = getattr(obj, "tags", None)
    if not tags:
        return None
    names = [getattr(t, "name", None) or getattr(t, "slug", "") for t in tags]
    names = [n for n in names if n]
    return ("Tags: " + ", ".join(names)) if names else None


def _entry_text(e) -> str:
    return "\n".join(filter(None, [e.title, e.summary, e.description, str(e.data_json or ""), _tags_line(e)]))


def _resource_text(r) -> str:
    return "\n".join(filter(None, [r.name, r.description, r.url, _tags_line(r)]))


def _asset_text(a) -> str:
    return "\n".join(filter(None, [a.name, a.alt_text, a.description, _tags_line(a)]))


def purge_embeddings(session: Session, group_id: UUID4, entity_type: str, entity_id: UUID4, model: str | None = None) -> int:
    """Remove an entity's embedding chunks (all models, or one). Called when the entity is deleted."""
    from marvin.db.models.groups.ai_embeddings import AIEmbeddingModel

    q = session.query(AIEmbeddingModel).filter_by(group_id=group_id, entity_type=entity_type, entity_id=entity_id)
    if model:
        q = q.filter_by(model_id=model)
    n = q.delete()
    session.commit()
    return n


def index_entry(session: Session, group_id: UUID4, entry, provider, model: str) -> int:
    """(Re)index a single entry. Convenience wrapper for auto-embed-on-publish. Returns chunk count."""
    return index_entity(session, group_id, "entry", entry.id, _entry_text(entry), provider, model)


def reindex_workspace(session: Session, group_id: UUID4, provider, model: str) -> tuple[int, int]:
    """(Re)index every indexable entity in a workspace. Returns (entities, chunks).

    Iterates the indexable-type registry, so a newly registered type is included automatically.
    """
    from marvin.services.ai.embeddings_registry import REGISTRY

    entities = chunks = 0
    for desc in REGISTRY.values():
        for obj in session.query(desc.model).filter_by(group_id=group_id).all():
            try:
                chunks += index_entity(session, group_id, desc.entity_type, obj.id, desc.text(obj), provider, model)
                entities += 1
            except Exception:
                continue  # skip a failing entity rather than aborting the whole workspace
    return entities, chunks
    return entities, chunks


def search_embeddings(
    session: Session,
    group_id: UUID4,
    query_vector: list[float],
    limit: int = 5,
    entity_types: list[str] | None = None,
) -> list[dict]:
    """Return the top-`limit` chunks by cosine similarity to `query_vector`."""
    import numpy as np

    from marvin.db.models.groups.ai_embeddings import AIEmbeddingModel

    q = session.query(AIEmbeddingModel).filter_by(group_id=group_id)
    if entity_types:
        q = q.filter(AIEmbeddingModel.entity_type.in_(entity_types))
    rows = q.all()
    if not rows:
        return []

    qv = np.asarray(query_vector, dtype=float)
    qn = float(np.linalg.norm(qv)) or 1.0

    scored: list[tuple[float, object]] = []
    for r in rows:
        v = np.asarray(r.embedding, dtype=float)
        if v.shape != qv.shape:
            continue  # dimension mismatch (different embedding model) — skip
        denom = (float(np.linalg.norm(v)) * qn) or 1.0
        scored.append((float(np.dot(v, qv) / denom), r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "text": r.chunk_text,
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id),
            "score": round(s, 4),
        }
        for s, r in scored[:limit]
    ]

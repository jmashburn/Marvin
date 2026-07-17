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


def default_embedding_model(provider_type: str) -> str | None:
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
    from marvin.db.models.groups.ai_embeddings import AIEmbeddingModel

    chunks = chunk_text(text)
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

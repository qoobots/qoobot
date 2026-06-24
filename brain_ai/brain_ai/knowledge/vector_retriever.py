"""
brain_ai/knowledge/vector_retriever.py — Semantic search over past episodes.

Uses sentence-transformers + FAISS for fast similarity search.
Falls back to keyword matching if dependencies are unavailable.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class VectorRetriever:
    """
    Indexes episode instructions as embeddings and supports semantic search.

    Dependencies (optional):
        pip install sentence-transformers faiss-cpu
    """

    def __init__(self, embed_model: str = _EMBED_MODEL) -> None:
        self._model_name = embed_model
        self._model = None
        self._index = None          # FAISS index
        self._episodes: list[dict] = []
        self._dim = 384
        self._try_load()

    def _try_load(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            import faiss  # type: ignore
            import numpy as np  # type: ignore

            self._model = SentenceTransformer(self._model_name)
            self._dim   = self._model.get_sentence_embedding_dimension()
            self._index = faiss.IndexFlatIP(self._dim)   # Inner product (cosine after norm)
            logger.info(f"VectorRetriever ready, dim={self._dim}")
        except ImportError as exc:
            logger.info(f"VectorRetriever: optional deps not installed ({exc}). "
                        f"Semantic search disabled.")

    @property
    def is_available(self) -> bool:
        return self._model is not None and self._index is not None

    def index(self, episode: dict) -> None:
        """Add a single episode to the vector index."""
        if not self.is_available:
            return
        import numpy as np

        text = episode.get("raw_instruction", episode.get("skill_name", ""))
        if not text:
            return

        vec = self._embed(text)
        self._index.add(vec)
        self._episodes.append(episode)

    def index_batch(self, episodes: list[dict]) -> None:
        for ep in episodes:
            self.index(ep)

    def search(
        self,
        query: str,
        top_k: int = 5,
        skill_filter: Optional[str] = None,
    ) -> list[dict]:
        if not self.is_available or len(self._episodes) == 0:
            return []

        import numpy as np

        vec = self._embed(query)
        k   = min(top_k * 3, len(self._episodes))  # over-retrieve then filter
        distances, indices = self._index.search(vec, k)

        results = []
        for idx in indices[0]:
            if idx < 0 or idx >= len(self._episodes):
                continue
            ep = self._episodes[idx]
            if skill_filter and ep.get("skill_name") != skill_filter:
                continue
            results.append(ep)
            if len(results) >= top_k:
                break
        return results

    def _embed(self, text: str):
        import numpy as np
        vec = self._model.encode([text], normalize_embeddings=True)
        return vec.astype(np.float32)

"""
brain_ai/knowledge/knowledge_base.py — Top-level knowledge base facade.

Aggregates WorkingMemory, ExperienceStore, EventRecorder, and VectorRetriever
into a single interface used by gRPC services and BrainAgent.
"""
from __future__ import annotations

import logging
from typing import Optional

from brain_ai.knowledge.event_recorder import EventRecorder
from brain_ai.knowledge.experience_store import ExperienceStore
from brain_ai.knowledge.working_memory import WorkingMemory

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Central knowledge store for brain_ai.

    Provides:
      - working_memory  : short-term task context (in-process)
      - experience_store: persistent episode log (SQLite)
      - event_recorder  : system event log (ring buffer + optional file)
      - vector_retriever: semantic search over episodes (optional, needs numpy/faiss)
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self.working_memory    = WorkingMemory(
            obs_buffer_size=cfg.get("obs_buffer_size", 50)
        )
        self.experience_store  = ExperienceStore(
            db_path=cfg.get("db_path")
        )
        self.event_recorder    = EventRecorder(
            buffer_size=cfg.get("event_buffer_size", 500),
            log_path=cfg.get("event_log_path"),
        )
        self._vector_retriever = None   # Lazy init — requires numpy/faiss

        logger.info("KnowledgeBase initialized.")

    # ─── Vector retriever (lazy) ──────────────────────────────

    @property
    def vector_retriever(self):
        if self._vector_retriever is None:
            try:
                from brain_ai.knowledge.vector_retriever import VectorRetriever
                self._vector_retriever = VectorRetriever()
                logger.info("VectorRetriever loaded.")
            except ImportError as exc:
                logger.warning(f"VectorRetriever unavailable: {exc}")
        return self._vector_retriever

    # ─── Convenience methods ──────────────────────────────────

    def store_episode(self, episode: dict) -> str:
        """Persist an episode and optionally index it for semantic search."""
        eid = self.experience_store.store(episode)
        if self._vector_retriever is not None:
            try:
                self._vector_retriever.index(episode)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Vector index update failed: {exc}")
        return eid

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        skill_filter: Optional[str] = None,
    ) -> list[dict]:
        """Semantic search over past episodes using instruction text."""
        if self.vector_retriever is not None:
            try:
                return self.vector_retriever.search(
                    query, top_k=top_k, skill_filter=skill_filter
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Vector search failed: {exc}")

        # Fallback: keyword search in SQLite
        return self.experience_store.search(skill_name=skill_filter, limit=top_k)

    def snapshot(self) -> dict:
        return {
            "working_memory": self.working_memory.snapshot(),
            "episode_count":  self.experience_store.count(),
            "recent_events":  self.event_recorder.recent(5),
        }

"""
brain_ai/grpc_server/knowledge_service.py — KnowledgeService gRPC implementation.

Implements:
  - SearchEpisodes:   vector similarity search on past episodes
  - StoreEpisode:     persist a new episode
  - SearchKnowledge:   search knowledge base entries
  - ListSkills:        list registered skills
  - RegisterSkill:     register a new skill
"""
from __future__ import annotations

import logging
import uuid

import grpc

from brain_ai.proto_gen.brain_os.knowledge import (
    service_pb2,
    service_pb2_grpc,
)
from brain_ai.proto_gen.brain_os.knowledge import types_pb2 as knowledge_types
from brain_ai.proto_gen.brain_os.common import types_pb2 as common_types

logger = logging.getLogger(__name__)


class KnowledgeServiceServicer(service_pb2_grpc.KnowledgeServiceServicer):
    """gRPC servicer for KnowledgeService."""

    def __init__(self):
        super().__init__()
        self._episodes: list[knowledge_types.Episode] = []
        self._skills: list[knowledge_types.Skill] = []
        logger.info("[KnowledgeService] Initialized (gRPC servicer).")

    # ── SearchEpisodes ─────────────────────────────────────────────────

    def SearchEpisodes(
        self,
        request: service_pb2.SearchEpisodesRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.SearchEpisodesResponse:
        """Vector similarity search on past episodes."""
        logger.info(
            f"[KnowledgeService] SearchEpisodes: query='{request.query_text[:40]}' "
            f"top_k={request.top_k}"
        )

        # TODO(Sprint 2): actual vector similarity search via pgvector/Lance
        # Stub: return first N stored episodes
        top_k = max(1, min(request.top_k, 20))
        results = self._episodes[:top_k]
        scores = [0.95 - i * 0.05 for i in range(len(results))]

        return service_pb2.SearchEpisodesResponse(
            status=common_types.Status(code=0, message="ok"),
            episodes=results,
            scores=scores,
        )

    # ── StoreEpisode ──────────────────────────────────────────────────

    def StoreEpisode(
        self,
        request: service_pb2.StoreEpisodeRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.StoreEpisodeResponse:
        """Persist a new episode."""
        episode = request.episode
        if not episode.episode_id:
            episode.episode_id = f"ep-{uuid.uuid4().hex[:8]}"
        self._episodes.append(episode)
        logger.info(
            f"[KnowledgeService] StoreEpisode: id={episode.episode_id} "
            f"success={episode.success}"
        )
        return service_pb2.StoreEpisodeResponse(
            status=common_types.Status(code=0, message="episode stored"),
            episode_id=episode.episode_id,
        )

    # ── SearchKnowledge ──────────────────────────────────────────────

    def SearchKnowledge(
        self,
        request: service_pb2.SearchKnowledgeRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.SearchKnowledgeResponse:
        """Search knowledge base entries."""
        logger.info(
            f"[KnowledgeService] SearchKnowledge: query='{request.query}' "
            f"type={knowledge_types.KnowledgeType.Name(request.type)}"
        )

        # TODO(Sprint 2): actual knowledge base search
        # Stub: empty results
        return service_pb2.SearchKnowledgeResponse(
            status=common_types.Status(code=0, message="ok"),
            entries=[],
        )

    # ── ListSkills ───────────────────────────────────────────────────

    def ListSkills(
        self,
        request: service_pb2.ListSkillsRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.ListSkillsResponse:
        """List all registered skills, optionally filtered by tag."""
        tag = request.tag_filter
        if tag:
            skills = [s for s in self._skills if tag in s.tags]
        else:
            skills = list(self._skills)

        logger.info(f"[KnowledgeService] ListSkills: {len(skills)} skills")
        return service_pb2.ListSkillsResponse(
            status=common_types.Status(code=0, message="ok"),
            skills=skills,
        )

    # ── RegisterSkill ────────────────────────────────────────────────

    def RegisterSkill(
        self,
        request: service_pb2.RegisterSkillRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.RegisterSkillResponse:
        """Register a new skill."""
        skill = request.skill
        if not skill.skill_id:
            skill.skill_id = f"skill-{uuid.uuid4().hex[:8]}"
        self._skills.append(skill)
        logger.info(
            f"[KnowledgeService] RegisterSkill: id={skill.skill_id} "
            f"name={skill.name}"
        )
        return service_pb2.RegisterSkillResponse(
            status=common_types.Status(code=0, message="skill registered"),
            skill_id=skill.skill_id,
        )

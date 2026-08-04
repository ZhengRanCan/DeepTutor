"""Synthetic-only adapter for the F41 pre-class semantic-context route."""

from __future__ import annotations

import hashlib
from typing import Any

from deeptutor.fusion.preclass_contracts import parse_preclass_teaching_context_proposal


def build_synthetic_proposal(request: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, non-personal proposal from an already parsed request.

    F41 intentionally does not access a learner profile, memory, model, or agent.
    The learner is authorized at the route boundary and never enters this payload.
    """
    request_fingerprint = hashlib.sha256(
        f"{request['semanticRequestId']}:{request['semanticRequestRevision']}".encode("utf-8")
    ).hexdigest()[:16]
    proposal = {
        "schemaVersion": request["schemaVersion"],
        "proposalId": f"synthetic-proposal-{request_fingerprint}",
        "basedOnSemanticRequestId": request["semanticRequestId"],
        "basedOnSemanticRequestRevision": request["semanticRequestRevision"],
        "semanticRequestDigest": request["semanticRequestDigest"],
        "resolutionStatus": "ready",
        "interpretedLessonSemantics": {
            "normalizedTopic": request["normalizedTopic"],
            "normalizedLearningObjectives": request["normalizedLearningObjectives"],
        },
        "lessonKnowledgeMap": {
            "mappingId": f"synthetic-map-{request['semanticRequestDigest'][7:23]}",
            "mappingRevision": "synthetic-v1",
            "knowledgeRefs": request["requestedKnowledgeRefs"],
        },
        "learnerCognitiveProjection": {
            "projectionRevision": "synthetic-development-v1",
            "signals": ["synthetic_fixture_only"],
        },
        "teachingGuidance": {
            "guidanceRevision": "synthetic-development-v1",
            "recommendedApproaches": ["worked-example"],
        },
        "sourceRevisions": ["synthetic-fixture-v1"],
        "clarificationIssues": [],
        "warnings": ["synthetic_development_source"],
        "createdAt": "2026-07-31T15:00:00Z",
    }
    return parse_preclass_teaching_context_proposal(proposal, request)

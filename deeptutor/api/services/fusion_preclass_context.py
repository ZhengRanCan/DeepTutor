"""F44 real, bounded pre-class decision pipeline over learner-scoped Book data."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from deeptutor.book.models import Progress
from deeptutor.book.storage import BookStorage, get_book_storage
from deeptutor.fusion.preclass_contracts import parse_preclass_teaching_context_proposal

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "class",
    "course",
    "explain",
    "for",
    "in",
    "intro",
    "introduction",
    "lesson",
    "of",
    "the",
    "to",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE)
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _matches(query: str, candidate: str) -> bool:
    query, candidate = query.casefold().strip(), candidate.casefold().strip()
    if not query or not candidate:
        return False
    if len(candidate) >= 3 and (candidate in query or query in candidate):
        return True
    candidate_tokens = _tokens(candidate)
    overlap = _tokens(query) & candidate_tokens
    return len(overlap) >= min(2, len(candidate_tokens)) if candidate_tokens else False


def _ref_id(kind: str, book_id: str, object_id: str) -> str:
    digest = hashlib.sha256(f"{kind}\0{book_id}\0{object_id}".encode("utf-8")).hexdigest()[:24]
    return f"{kind}-{digest}"


def _projection(progress_items: list[Progress]) -> tuple[list[str], list[str], list[str]]:
    if not progress_items:
        return ["insufficient_data"], ["diagnostic-checkpoint-first"], ["insufficient_data"]
    signals = ["progress_available"]
    scores = [item.score for item in progress_items]
    average = sum(scores) / len(scores)
    if average < 40:
        signals.append("score_band_low")
        guidance = ["worked-example-first", "retrieval-practice"]
    elif average < 75:
        signals.append("score_band_medium")
        guidance = ["guided-practice", "retrieval-practice"]
    else:
        signals.append("score_band_high")
        guidance = ["guided-practice", "transfer-challenge"]
    if any(item.weak_chapters for item in progress_items):
        signals.append("weak_area_present")
        guidance.insert(0, "targeted-retrieval-practice")
    if any(item.visited_page_ids for item in progress_items):
        signals.append("course_started")
    return sorted(set(signals)), list(dict.fromkeys(guidance)), []


def _semantic_signal_too_vague(request: dict[str, Any]) -> bool:
    query = " ".join([request["normalizedTopic"], *request["normalizedLearningObjectives"]])
    return len(_tokens(query)) < 2


def _base_proposal(
    request: dict[str, Any], binding: dict[str, Any], *, status: str
) -> dict[str, Any]:
    scope_revision = str(binding["courseScopeRevision"])
    return {
        "schemaVersion": request["schemaVersion"],
        "proposalId": f"proposal-{hashlib.sha256((request['semanticRequestDigest'] + scope_revision).encode()).hexdigest()[:24]}",
        "basedOnSemanticRequestId": request["semanticRequestId"],
        "basedOnSemanticRequestRevision": request["semanticRequestRevision"],
        "semanticRequestDigest": request["semanticRequestDigest"],
        "resolutionStatus": status,
        "interpretedLessonSemantics": {
            "normalizedTopic": request["normalizedTopic"],
            "normalizedLearningObjectives": request["normalizedLearningObjectives"],
        },
        "lessonKnowledgeMap": {
            "mappingId": f"map-{hashlib.sha256((request['semanticRequestDigest'] + scope_revision).encode()).hexdigest()[:24]}",
            "mappingRevision": scope_revision,
            "knowledgeRefs": [],
        },
        "learnerCognitiveProjection": {
            "projectionRevision": scope_revision,
            "signals": [],
        },
        "teachingGuidance": {
            "guidanceRevision": "bounded-policy-v1",
            "recommendedApproaches": [],
        },
        "sourceRevisions": [f"course-scope:{scope_revision}"],
        "clarificationIssues": [],
        "warnings": [],
        "createdAt": _now(),
    }


def build_failed_proposal(
    request: dict[str, Any], binding: dict[str, Any], reason: str
) -> dict[str, Any]:
    proposal = _base_proposal(request, binding, status="unresolved")
    proposal["clarificationIssues"] = [reason]
    proposal["warnings"] = ["decision_pipeline_failed"]
    return parse_preclass_teaching_context_proposal(proposal, request)


def build_real_proposal(
    request: dict[str, Any], binding: dict[str, Any], storage: BookStorage | None = None
) -> dict[str, Any]:
    """Return a minimal proposal derived only from the bound learner workspace."""
    store = storage or get_book_storage()
    query = " ".join([request["normalizedTopic"], *request["normalizedLearningObjectives"]])
    scope_id = str(binding["courseScopeId"])
    proposal = _base_proposal(request, binding, status="ready")
    if _semantic_signal_too_vague(request):
        proposal["resolutionStatus"] = "needs_clarification"
        proposal["clarificationIssues"] = ["requirement_ambiguous"]
        proposal["warnings"] = ["request_too_vague"]
        return parse_preclass_teaching_context_proposal(proposal, request)
    refs: list[dict[str, str]] = []
    progress_items: list[Progress] = []
    source_revisions = list(proposal["sourceRevisions"])

    for book_id in binding["bookIds"]:
        book = store.load_book(book_id)
        if book is None:
            continue
        spine = store.load_spine(book_id)
        book_text = " ".join((book.title, book.description))
        matched_nodes = (
            []
            if spine is None
            else [
                node
                for node in spine.concept_graph.nodes
                if _matches(query, " ".join((node.label, node.description)))
            ]
        )
        matched_chapters = (
            []
            if spine is None
            else [
                chapter
                for chapter in spine.chapters
                if _matches(
                    query,
                    " ".join((chapter.title, chapter.summary, *chapter.learning_objectives)),
                )
            ]
        )
        if not (_matches(query, book_text) or matched_nodes or matched_chapters):
            continue
        for node in matched_nodes:
            refs.append(
                {
                    "namespace": "deeptutor",
                    "scopeId": scope_id,
                    "id": _ref_id("concept", book_id, node.id or node.label),
                }
            )
        for chapter in matched_chapters:
            refs.append(
                {
                    "namespace": "deeptutor",
                    "scopeId": scope_id,
                    "id": _ref_id("chapter", book_id, chapter.id),
                }
            )
        if not matched_nodes and not matched_chapters:
            refs.append(
                {
                    "namespace": "deeptutor",
                    "scopeId": scope_id,
                    "id": _ref_id("book", book_id, book_id),
                }
            )
        source_revisions.append(f"book:{book_id}:{book.updated_at}")
        if spine is not None:
            source_revisions.append(f"spine:{book_id}:{spine.version}:{spine.updated_at}")
        progress = store.load_progress(book_id)
        if progress is not None:
            progress_items.append(progress)
            source_revisions.append(f"progress:{book_id}:{progress.updated_at}")

    unique_refs = {(ref["namespace"], ref["scopeId"], ref["id"]): ref for ref in refs}
    refs = [unique_refs[key] for key in sorted(unique_refs)][:32]
    if not refs:
        proposal["resolutionStatus"] = "unresolved"
        proposal["clarificationIssues"] = ["knowledge_scope_unresolved"]
        proposal["warnings"] = ["no_semantic_match_in_course_scope"]
        return parse_preclass_teaching_context_proposal(proposal, request)

    signals, guidance, warnings = _projection(progress_items)
    map_fingerprint = hashlib.sha256(
        "\0".join(ref["id"] for ref in refs).encode("utf-8")
    ).hexdigest()[:24]
    proposal["lessonKnowledgeMap"] = {
        "mappingId": f"map-{map_fingerprint}",
        "mappingRevision": str(binding["courseScopeRevision"]),
        "knowledgeRefs": refs,
    }
    proposal["learnerCognitiveProjection"] = {
        "projectionRevision": f"projection-{map_fingerprint}",
        "signals": signals,
    }
    proposal["teachingGuidance"] = {
        "guidanceRevision": "bounded-policy-v1",
        "recommendedApproaches": guidance,
    }
    proposal["sourceRevisions"] = source_revisions
    proposal["warnings"] = warnings
    return parse_preclass_teaching_context_proposal(proposal, request)


__all__ = ["build_failed_proposal", "build_real_proposal"]

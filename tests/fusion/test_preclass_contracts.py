from __future__ import annotations

import json
from pathlib import Path

import pytest

from deeptutor.fusion.preclass_contracts import (
    PRECLASS_CONTRACT_VERSION,
    PreClassContractError,
    canonicalize_digest_envelope,
    compute_semantic_request_digest,
    digest_canonical_bytes,
    parse_frozen_lesson_generation_context,
    parse_lesson_semantic_request,
    parse_strict_json,
)

FIXTURES = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "docs/harness/FUSION/fixtures/canonical-digest-v1.json"
    ).read_text(encoding="utf-8")
)
SEMANTIC = FIXTURES["successCases"][0]


def request(**overrides: object) -> dict[str, object]:
    return {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "semanticRequestId": "request-01",
        "semanticRequestRevision": "1",
        "lessonSessionId": "lesson-01",
        "semanticRequestDigest": SEMANTIC["sha256"],
        **SEMANTIC["canonicalValue"],
        "warnings": [],
        **overrides,
    }


def proposal(digest: str | None = None) -> dict[str, object]:
    canonical = SEMANTIC["canonicalValue"]
    return {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "proposalId": "proposal-01",
        "basedOnSemanticRequestId": "request-01",
        "basedOnSemanticRequestRevision": "1",
        "semanticRequestDigest": digest or SEMANTIC["sha256"],
        "resolutionStatus": "ready",
        "interpretedLessonSemantics": {
            "normalizedTopic": canonical["normalizedTopic"],
            "normalizedLearningObjectives": canonical["normalizedLearningObjectives"],
        },
        "lessonKnowledgeMap": {
            "mappingId": "map-01",
            "mappingRevision": "1",
            "knowledgeRefs": canonical["requestedKnowledgeRefs"],
        },
        "learnerCognitiveProjection": {"projectionRevision": "1", "signals": ["synthetic-signal"]},
        "teachingGuidance": {"guidanceRevision": "1", "recommendedApproaches": ["worked-example"]},
        "sourceRevisions": ["source-1"],
        "clarificationIssues": [],
        "warnings": [],
        "createdAt": "2026-07-31T15:00:00Z",
    }


def test_shared_fixture_produces_identical_canonical_bytes_and_digests() -> None:
    for entry in FIXTURES["successCases"]:
        output = canonicalize_digest_envelope(
            entry["purpose"], entry["valueSchemaVersion"], entry["canonicalValue"]
        )
        assert output.decode("utf-8") == entry["canonicalJson"]
        assert len(output) == entry["utf8ByteLength"]
        assert digest_canonical_bytes(output) == entry["sha256"]


def test_lesson_semantic_request_is_strict_and_digest_bound() -> None:
    parsed = parse_lesson_semantic_request(request())
    assert compute_semantic_request_digest(parsed) == SEMANTIC["sha256"]
    assert parsed["sourceMaterialRefs"][0]["materialId"] == "material-01"


@pytest.mark.parametrize(
    ("code", "run"),
    [
        (
            "unknown_field",
            lambda: parse_lesson_semantic_request(request(sceneId="browser-command")),
        ),
        (
            "unsupported_schema_version",
            lambda: parse_lesson_semantic_request(request(schemaVersion="v2")),
        ),
        (
            "digest_mismatch",
            lambda: parse_lesson_semantic_request(
                request(semanticRequestDigest="sha256:" + "e" * 64)
            ),
        ),
        (
            "unauthorized_reference",
            lambda: parse_lesson_semantic_request(
                request(
                    requestedKnowledgeRefs=[
                        {
                            "namespace": "deeptutor",
                            "scopeId": "other-scope",
                            "id": "kp-linear-slope",
                        }
                    ]
                )
            ),
        ),
        ("duplicate_key", lambda: parse_strict_json('{"topic":"one","topic":"two"}')),
        ("normalized_key_collision", lambda: parse_strict_json('{"e\\u0301":1,"é":2}')),
        ("invalid_unicode", lambda: parse_strict_json('{"topic":"\\ud800"}')),
        ("unsafe_integer", lambda: parse_strict_json('{"count":9007199254740992}')),
        ("payload_too_large", lambda: parse_strict_json("x" * (256 * 1024 + 1))),
    ],
)
def test_parser_fails_closed(code: str, run: object) -> None:
    with pytest.raises(PreClassContractError, match=code) as error:
        run()  # type: ignore[operator]
    assert error.value.code == code


def test_frozen_context_rejects_ui_fields_and_revision_mismatch() -> None:
    context = {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "contextId": "context-01",
        "semanticRequest": request(),
        "proposal": proposal(),
        "resolution": {
            "schemaVersion": PRECLASS_CONTRACT_VERSION,
            "semanticRequestId": "request-01",
            "semanticRequestRevision": "1",
            "semanticRequestDigest": SEMANTIC["sha256"],
            "status": "ready",
            "clarificationIssues": [],
        },
        "frozenAt": "2026-07-31T15:00:00Z",
    }
    assert parse_frozen_lesson_generation_context(context)["frozenAt"] == "2026-07-31T15:00:00.000Z"
    with pytest.raises(PreClassContractError, match="unknown_field"):
        parse_frozen_lesson_generation_context(
            {**context, "proposal": {**proposal(), "sceneId": "forbidden"}}
        )
    with pytest.raises(PreClassContractError, match="semantic_request_mismatch"):
        parse_frozen_lesson_generation_context(
            {**context, "resolution": {**context["resolution"], "semanticRequestRevision": "2"}}
        )
    with pytest.raises(PreClassContractError, match="timestamp_precision_unsupported"):
        parse_frozen_lesson_generation_context({**context, "frozenAt": "2026-07-31T15:00:00.1234Z"})

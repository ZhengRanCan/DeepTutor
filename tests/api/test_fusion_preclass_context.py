from __future__ import annotations

import json

from fastapi.testclient import TestClient

from deeptutor.api.routers.fusion_test_app import create_app
from deeptutor.api.services.fusion_course_scope import CourseScopeRegistry
from deeptutor.api.services.fusion_delegation import exchange_launch_code, issue_launch_code
from deeptutor.book.models import (
    Book,
    BookStatus,
    Chapter,
    ConceptGraph,
    ConceptNode,
    Progress,
    Spine,
)
from deeptutor.book.storage import get_book_storage
from deeptutor.fusion.preclass_contracts import (
    PRECLASS_CONTRACT_VERSION,
    compute_semantic_request_digest,
)
from deeptutor.multi_user.models import CurrentUser
from deeptutor.multi_user.paths import scope_for_user, user_context


def semantic_request(scope_id: str, **overrides: object) -> dict[str, object]:
    draft: dict[str, object] = {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "semanticRequestId": "request-44",
        "semanticRequestRevision": "1",
        "lessonSessionId": "lesson-44",
        "semanticRequestDigest": "sha256:" + "0" * 64,
        "normalizedTopic": "Explain linear functions",
        "normalizedLearningObjectives": ["Understand slope in linear functions"],
        "authorizedKnowledgeScope": {
            "namespace": "deeptutor",
            "scopeId": scope_id,
            "allowedKnowledgeRefs": [],
        },
        "audienceSemantics": {"audienceType": "classroom", "language": "en"},
        "teachingConstraints": {"durationMinutes": 15},
        "requestedKnowledgeRefs": [],
        "sourceMaterialRefs": [],
        "warnings": [],
        **overrides,
    }
    draft["semanticRequestDigest"] = compute_semantic_request_digest(draft)
    return draft


def setup_real_scope(monkeypatch, tmp_path, *, with_progress: bool):
    from deeptutor.api.routers import fusion_preclass_context as route_module
    from deeptutor.api.services import fusion_course_scope as scope_module
    from deeptutor.book import storage as storage_module
    from deeptutor.multi_user import paths

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(paths, "USERS_ROOT", tmp_path / "users")
    paths._path_services.clear()  # noqa: SLF001
    storage_module._storages.clear()  # noqa: SLF001
    learner_id = "learner-real-44"
    learner = CurrentUser(
        id=learner_id,
        username="learner",
        role="user",
        scope=scope_for_user(learner_id, is_admin=False),
    )
    with user_context(learner):
        storage = get_book_storage()
        storage.save_book(Book(id="book-linear", title="Linear Functions", status=BookStatus.READY))
        storage.save_spine(
            Spine(
                book_id="book-linear",
                version=3,
                chapters=[
                    Chapter(
                        id="chapter-slope",
                        title="Slope in linear functions",
                        learning_objectives=["Interpret slope"],
                    )
                ],
                concept_graph=ConceptGraph(
                    nodes=[
                        ConceptNode(
                            id="linear_slope",
                            label="Slope in linear functions",
                            chapter_id="chapter-slope",
                        )
                    ]
                ),
            )
        )
        if with_progress:
            storage.save_progress(
                Progress(
                    book_id="book-linear",
                    visited_page_ids=["page-1"],
                    weak_chapters=["chapter-slope"],
                    score=35,
                )
            )
        registry = CourseScopeRegistry(tmp_path / "course-scopes.json")
        scope = registry.create_scope(learner_id, ["book-linear"], storage)
    monkeypatch.setattr(scope_module, "get_course_scope_registry", lambda: registry)
    monkeypatch.setattr(route_module, "get_course_scope_registry", lambda: registry)
    code = issue_launch_code(learner_id, scope)
    credential = exchange_launch_code(code, "openmaic", "lesson-44")
    assert credential
    headers = {"Authorization": f"Bearer {credential['token']}"}
    return TestClient(create_app()), headers, registry, scope


def test_real_route_maps_bound_book_and_returns_minimal_progress_projection(
    monkeypatch, tmp_path
) -> None:
    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=True)
    response = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request(str(scope["courseScopeId"])),
        headers=headers,
    )

    assert response.status_code == 200
    proposal = response.json()
    assert proposal["resolutionStatus"] == "ready"
    assert proposal["lessonKnowledgeMap"]["knowledgeRefs"]
    assert {ref["scopeId"] for ref in proposal["lessonKnowledgeMap"]["knowledgeRefs"]} == {
        scope["courseScopeId"]
    }
    assert proposal["learnerCognitiveProjection"]["signals"] == [
        "course_started",
        "progress_available",
        "score_band_low",
        "weak_area_present",
    ]
    assert proposal["teachingGuidance"]["recommendedApproaches"][0] == (
        "targeted-retrieval-practice"
    )
    serialized = json.dumps(proposal).lower()
    for forbidden in ("learner-real-44", "user_answer", "memory", "token", "thought"):
        assert forbidden not in serialized


def test_missing_progress_is_ready_with_insufficient_data(monkeypatch, tmp_path) -> None:
    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)
    proposal = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request(str(scope["courseScopeId"])),
        headers=headers,
    ).json()
    assert proposal["resolutionStatus"] == "ready"
    assert proposal["learnerCognitiveProjection"]["signals"] == ["insufficient_data"]
    assert proposal["teachingGuidance"]["recommendedApproaches"] == ["diagnostic-checkpoint-first"]


def test_scope_mismatch_and_revoke_fail_closed(monkeypatch, tmp_path) -> None:
    client, headers, registry, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)
    wrong = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request("course-other"),
        headers=headers,
    )
    assert wrong.status_code == 403
    assert wrong.json()["detail"] == "course_scope_mismatch"

    registry.revoke("learner-real-44", str(scope["courseScopeId"]))
    revoked = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request(str(scope["courseScopeId"])),
        headers=headers,
    )
    assert revoked.status_code == 403
    assert revoked.json()["detail"] == "course_scope_revoked"


def test_unmatched_topic_is_explicitly_unresolved(monkeypatch, tmp_path) -> None:
    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)
    proposal = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request(
            str(scope["courseScopeId"]),
            normalizedTopic="Medieval poetry",
            normalizedLearningObjectives=["Analyze a sonnet"],
        ),
        headers=headers,
    ).json()
    assert proposal["resolutionStatus"] == "unresolved"
    assert proposal["clarificationIssues"] == ["knowledge_scope_unresolved"]
    assert proposal["lessonKnowledgeMap"]["knowledgeRefs"] == []


def test_decision_failure_returns_stable_unresolved_result(monkeypatch, tmp_path) -> None:
    from deeptutor.api.routers import fusion_preclass_context as route_module

    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)

    def fail(*_args, **_kwargs):
        raise RuntimeError("private failure detail")

    monkeypatch.setattr(route_module, "build_real_proposal", fail)
    proposal = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request(str(scope["courseScopeId"])),
        headers=headers,
    ).json()
    assert proposal["resolutionStatus"] == "unresolved"
    assert proposal["clarificationIssues"] == ["decision_pipeline_unavailable"]
    assert proposal["warnings"] == ["decision_pipeline_failed"]
    assert "private failure detail" not in json.dumps(proposal)


def test_route_still_rejects_contract_and_delegation_errors(monkeypatch, tmp_path) -> None:
    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)
    invalid = semantic_request(str(scope["courseScopeId"]))
    invalid["learnerId"] = "browser-override"
    assert (
        client.post("/api/v1/fusion/pre-class/context", json=invalid, headers=headers).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            json=semantic_request(str(scope["courseScopeId"]), lessonSessionId="wrong-lesson"),
            headers=headers,
        ).status_code
        == 403
    )


def test_ambiguous_topic_requests_explicit_clarification(monkeypatch, tmp_path) -> None:
    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)
    proposal = client.post(
        "/api/v1/fusion/pre-class/context",
        json=semantic_request(
            str(scope["courseScopeId"]),
            normalizedTopic="Introduction",
            normalizedLearningObjectives=["Overview"],
        ),
        headers=headers,
    ).json()
    assert proposal["resolutionStatus"] == "needs_clarification"
    assert proposal["clarificationIssues"] == ["requirement_ambiguous"]
    assert proposal["lessonKnowledgeMap"]["knowledgeRefs"] == []
    assert proposal["basedOnSemanticRequestRevision"] == "1"


def test_clarified_revision_resolves_to_a_new_ready_proposal(monkeypatch, tmp_path) -> None:
    client, headers, _, scope = setup_real_scope(monkeypatch, tmp_path, with_progress=False)
    revised = semantic_request(
        str(scope["courseScopeId"]),
        semanticRequestRevision="2",
        normalizedTopic="Explain slope in linear functions",
        normalizedLearningObjectives=["Interpret slope in linear functions"],
    )
    response = client.post("/api/v1/fusion/pre-class/context", json=revised, headers=headers)
    assert response.status_code == 200
    proposal = response.json()
    assert proposal["resolutionStatus"] == "ready"
    assert proposal["basedOnSemanticRequestRevision"] == "2"
    assert proposal["semanticRequestDigest"] == revised["semanticRequestDigest"]

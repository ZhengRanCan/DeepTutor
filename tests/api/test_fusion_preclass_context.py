from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from deeptutor.api.routers.fusion_test_app import create_app
import deeptutor.api.services.fusion_delegation as delegation_service
from deeptutor.api.services.fusion_delegation import exchange_launch_code, issue_launch_code
from deeptutor.fusion.preclass_contracts import PRECLASS_CONTRACT_VERSION

FIXTURES = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "docs/harness/FUSION/fixtures/canonical-digest-v1.json"
    ).read_text(encoding="utf-8")
)
SEMANTIC = FIXTURES["successCases"][0]


def semantic_request(**overrides: object) -> dict[str, object]:
    return {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "semanticRequestId": "request-41",
        "semanticRequestRevision": "1",
        "lessonSessionId": "lesson-41",
        "semanticRequestDigest": SEMANTIC["sha256"],
        **SEMANTIC["canonicalValue"],
        "warnings": [],
        **overrides,
    }


def client_and_headers(monkeypatch: object) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("ENVIRONMENT", "test")  # type: ignore[attr-defined]
    issued = exchange_launch_code(
        issue_launch_code("allowlisted-synthetic-learner"), "openmaic", "lesson-41"
    )
    assert issued
    return TestClient(create_app()), {"Authorization": f"Bearer {issued['token']}"}


def test_delegated_request_returns_one_explicitly_synthetic_proposal(monkeypatch) -> None:
    client, headers = client_and_headers(monkeypatch)
    response = client.post(
        "/api/v1/fusion/pre-class/context", json=semantic_request(), headers=headers
    )

    assert response.status_code == 200
    proposal = response.json()
    assert proposal["basedOnSemanticRequestId"] == "request-41"
    assert proposal["basedOnSemanticRequestRevision"] == "1"
    assert proposal["semanticRequestDigest"] == SEMANTIC["sha256"]
    assert proposal["sourceRevisions"] == ["synthetic-fixture-v1"]
    assert proposal["warnings"] == ["synthetic_development_source"]
    serialized = json.dumps(proposal)
    for forbidden in ("allowlisted-synthetic-learner", "token", "memory", "thought"):
        assert forbidden not in serialized.lower()


def test_route_rejects_session_scope_audience_and_expiry_failures(monkeypatch) -> None:
    client, headers = client_and_headers(monkeypatch)
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            json=semantic_request(lessonSessionId="wrong-lesson"),
            headers=headers,
        ).status_code
        == 403
    )

    scope_token = exchange_launch_code(
        issue_launch_code("allowlisted-synthetic-learner"), "openmaic", "lesson-41"
    )
    assert scope_token
    delegation_service._delegations[str(scope_token["token"])]["scope"].remove(  # noqa: SLF001
        "preclass-context:read"
    )
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            json=semantic_request(),
            headers={"Authorization": f"Bearer {scope_token['token']}"},
        ).status_code
        == 403
    )

    audience_token = exchange_launch_code(
        issue_launch_code("allowlisted-synthetic-learner"), "openmaic", "lesson-41"
    )
    assert audience_token
    delegation_service._delegations[str(audience_token["token"])]["audience"] = "other"  # noqa: SLF001
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            json=semantic_request(),
            headers={"Authorization": f"Bearer {audience_token['token']}"},
        ).status_code
        == 403
    )

    expired_token = exchange_launch_code(
        issue_launch_code("allowlisted-synthetic-learner"), "openmaic", "lesson-41"
    )
    assert expired_token
    monkeypatch.setattr(delegation_service.time, "time", lambda: 9_999_999_999)
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            json=semantic_request(),
            headers={"Authorization": f"Bearer {expired_token['token']}"},
        ).status_code
        == 403
    )


def test_route_fails_closed_for_contract_and_payload_errors(monkeypatch) -> None:
    client, headers = client_and_headers(monkeypatch)
    invalid_cases = [
        semantic_request(learnerId="browser-override"),
        semantic_request(schemaVersion="preclass-fusion-v2"),
        semantic_request(semanticRequestDigest="sha256:" + "e" * 64),
        semantic_request(
            requestedKnowledgeRefs=[
                {"namespace": "deeptutor", "scopeId": "not-authorized", "id": "kp-linear-slope"}
            ]
        ),
    ]
    for body in invalid_cases:
        assert (
            client.post("/api/v1/fusion/pre-class/context", json=body, headers=headers).status_code
            == 400
        )
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            content='{"schemaVersion":"one","schemaVersion":"two"}',
            headers=headers,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fusion/pre-class/context",
            content=b"x" * (256 * 1024 + 1),
            headers=headers,
        ).status_code
        == 413
    )


def test_synthetic_adapter_is_unavailable_in_production(monkeypatch) -> None:
    client, headers = client_and_headers(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    response = client.post(
        "/api/v1/fusion/pre-class/context", json=semantic_request(), headers=headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "synthetic_context_unavailable"

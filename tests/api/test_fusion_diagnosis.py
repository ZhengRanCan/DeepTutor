from fastapi import FastAPI
from fastapi.testclient import TestClient

from deeptutor.api.routers.fusion_diagnosis import router
from deeptutor.api.services.fusion_diagnosis import FIXED_KNOWLEDGE_POINT_ID


def event(correctness: str = "incorrect") -> dict[str, object]:
    return {
        "schemaVersion": "v1", "eventId": "event-1", "eventType": "checkpoint_submitted",
        "lessonSessionId": "lesson-1", "courseId": "course-1", "sceneId": "scene-1", "correlationId": "correlation-1",
        "checkpointId": "checkpoint-1", "mappingId": "map-1", "mappingRevision": "1",
        "lessonKnowledgePointIds": [FIXED_KNOWLEDGE_POINT_ID], "originalQuestion": "2 + 2 = ?", "studentAnswer": "3",
        "localAssessment": {"gradingMode": "exact", "correctness": correctness}, "occurredAt": "2026-07-24T00:00:00Z",
    }


def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("FUSION_DEVELOPMENT_MOCK_ENABLED", "true")
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/fusion")
    return TestClient(app)


def test_returns_same_event_id_and_deterministic_intent(monkeypatch) -> None:
    response = client(monkeypatch).post("/api/v1/fusion/diagnosis", json=event())
    assert response.status_code == 200
    body = response.json()
    assert body["eventId"] == "event-1"
    assert body["correctness"] == "incorrect"
    assert body["teachingIntent"]["recommendedStrategy"] == "development_mock_concrete_example"
    assert "sceneId" not in body and "learnerId" not in body


def test_correct_and_unknown_answers_are_deterministic(monkeypatch) -> None:
    api = client(monkeypatch)
    assert api.post("/api/v1/fusion/diagnosis", json=event("correct")).json()["teachingIntent"]["kind"] == "continue"
    assert api.post("/api/v1/fusion/diagnosis", json=event("unknown")).json()["correctness"] == "unknown"


def test_rejects_disabled_configuration_and_invalid_events(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FUSION_DEVELOPMENT_MOCK_ENABLED", "true")
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/fusion")
    assert TestClient(app).post("/api/v1/fusion/diagnosis", json=event()).status_code == 403
    api = client(monkeypatch)
    invalid = event()
    invalid["lessonKnowledgePointIds"] = ["untrusted"]
    assert api.post("/api/v1/fusion/diagnosis", json=invalid).status_code == 422

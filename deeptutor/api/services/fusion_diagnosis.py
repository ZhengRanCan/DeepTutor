"""Deterministic, Development Only diagnosis for the F08 Fusion boundary."""
from __future__ import annotations

from dataclasses import dataclass

FIXED_KNOWLEDGE_POINT_ID = "lesson-linear-function-slope"
SCHEMA_VERSION = "v1"


class FusionDiagnosisError(ValueError):
    pass


def diagnose_checkpoint(event: dict[str, object]) -> dict[str, object]:
    required = ("eventId", "lessonSessionId", "courseId", "sceneId", "correlationId", "checkpointId", "mappingId", "mappingRevision", "originalQuestion", "studentAnswer", "occurredAt")
    if event.get("schemaVersion") != SCHEMA_VERSION or event.get("eventType") != "checkpoint_submitted":
        raise FusionDiagnosisError("unsupported_schema_or_event")
    if any(not isinstance(event.get(key), str) or not event[key].strip() for key in required):
        raise FusionDiagnosisError("missing_required_field")
    points = event.get("lessonKnowledgePointIds")
    if points != [FIXED_KNOWLEDGE_POINT_ID]:
        raise FusionDiagnosisError("unknown_knowledge_point")
    assessment = event.get("localAssessment")
    if not isinstance(assessment, dict):
        raise FusionDiagnosisError("invalid_local_assessment")
    correctness = assessment.get("correctness", "unknown")
    if correctness not in {"correct", "incorrect", "partially_correct", "unknown"}:
        raise FusionDiagnosisError("invalid_correctness")
    correct = correctness == "correct"
    return {
        "schemaVersion": SCHEMA_VERSION, "eventId": event["eventId"], "correctness": correctness,
        "diagnoses": [] if correct else [{"lessonKnowledgePointId": FIXED_KNOWLEDGE_POINT_ID, "misconception": "development_mock_checkpoint_mismatch", "confidence": 1.0}],
        "teachingIntent": {"schemaVersion": SCHEMA_VERSION, "kind": "continue" if correct else "insert_remediation", "targetLessonKnowledgePointIds": [FIXED_KNOWLEDGE_POINT_ID], "recommendedStrategy": "development_mock_continue" if correct else "development_mock_concrete_example"},
        "warnings": ["development_mock_only"], "createdAt": event["occurredAt"],
    }

"""F40 pre-class contract parser and fusion-c14n-v1 digest implementation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import re
from typing import Any
import unicodedata

PRECLASS_CONTRACT_VERSION = "preclass-fusion-v1"
SEMANTIC_REQUEST_DIGEST_SCHEMA = "fusion-semantic-request-digest-v1"
FUSION_CANONICALIZATION = "fusion-c14n-v1"


class PreClassContractError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PreClassContractError(code)


def _record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("invalid_request")
    return value


def _fields(value: dict[str, Any], required: set[str], optional: set[str] | None = None) -> None:
    allowed = required | (optional or set())
    if set(value) - allowed:
        _fail("unknown_field")
    if required - set(value):
        _fail("missing_required_field")


def _text(value: Any, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        _fail("invalid_string")
    result = unicodedata.normalize("NFC", value)
    try:
        result.encode("utf-8")
    except UnicodeEncodeError:
        _fail("invalid_unicode")
    return result


def _identifier(value: Any) -> str:
    result = _text(value, 256)
    if not re.fullmatch(r"[\x21-\x7e]+", result):
        _fail("invalid_ascii_identifier")
    return result


def _digest(value: Any) -> str:
    result = _identifier(value)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", result):
        _fail("invalid_digest")
    return result


def _string_array(value: Any, maximum: int = 128) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        _fail("invalid_array")
    return [_text(item) for item in value]


def _string_set(value: Any, maximum: int = 128) -> list[str]:
    result = sorted(_identifier(item) for item in _string_array(value, maximum))
    if len(result) != len(set(result)):
        _fail("duplicate_set_member")
    return result


def _integer(value: Any, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
        _fail("unsafe_integer")
    return value


def _timestamp(value: Any) -> str:
    result = _text(value, 32)
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)", result):
        _fail("invalid_timestamp")
    fraction = re.search(r"\.(\d+)", result)
    if fraction and len(fraction.group(1)) > 3:
        _fail("timestamp_precision_unsupported")
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError:
        _fail("invalid_timestamp")
    return (
        parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{parsed.astimezone(timezone.utc).microsecond // 1000:03d}Z"
    )


def _ref(value: Any) -> dict[str, str]:
    item = _record(value)
    _fields(item, {"namespace", "scopeId", "id"})
    return {
        "namespace": _identifier(item["namespace"]),
        "scopeId": _identifier(item["scopeId"]),
        "id": _identifier(item["id"]),
    }


def _ref_key(value: dict[str, str]) -> tuple[str, str, str]:
    return value["namespace"], value["scopeId"], value["id"]


def _refs(value: Any, maximum: int = 128) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > maximum:
        _fail("invalid_array")
    result = sorted((_ref(item) for item in value), key=_ref_key)
    if len({_ref_key(item) for item in result}) != len(result):
        _fail("duplicate_set_member")
    return result


def _materials(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 64:
        _fail("invalid_array")
    result: list[dict[str, str]] = []
    for raw in value:
        item = _record(raw)
        _fields(item, {"materialId", "digest", "purpose"})
        result.append(
            {
                "materialId": _identifier(item["materialId"]),
                "digest": _digest(item["digest"]),
                "purpose": _identifier(item["purpose"]),
            }
        )
    result.sort(key=lambda item: item["materialId"])
    if len({item["materialId"] for item in result}) != len(result):
        _fail("duplicate_set_member")
    return result


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return _text(value, 1_000_000)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            _fail("unsafe_integer")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("invalid_number")
        if value.is_integer() and abs(value) > 9_007_199_254_740_991:
            _fail("unsafe_integer")
        return 0 if value == 0 else value
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if not isinstance(value, dict):
        _fail("canonicalization_failed")
    result: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = _text(key, 1_000_000)
        if normalized_key in result:
            _fail("normalized_key_collision")
        result[normalized_key] = _normalize(item)
    return result


def _jcs_number(value: float) -> str:
    """The v1 schemas only admit binary64; normalize the common ECMAScript forms."""
    if value == 0:
        return "0"
    rendered = repr(value)
    if "e" not in rendered:
        return rendered
    coefficient, exponent = rendered.split("e")
    exp = int(exponent)
    if -6 < exp < 21:
        return format(value, ".15f").rstrip("0").rstrip(".")
    return f"{coefficient}e{'+' if exp >= 0 else ''}{exp}"


def _canonical_json(value: Any) -> str:
    if isinstance(value, float):
        return _jcs_number(value)
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda item: item.encode("utf-16-be"))
        return (
            "{"
            + ",".join(
                json.dumps(key, ensure_ascii=False, separators=(",", ":"))
                + ":"
                + _canonical_json(value[key])
                for key in keys
            )
            + "}"
        )
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def canonicalize_digest_envelope(
    purpose: str, value_schema_version: str, canonical_value: Any
) -> bytes:
    if purpose not in {"semantic-request", "lesson-fact-set", "profile-update-candidate"}:
        _fail("unsupported_digest_purpose")
    if not re.fullmatch(r"fusion-[a-z0-9-]+-digest-v1", value_schema_version):
        _fail("unsupported_digest_schema")
    envelope = _normalize(
        {
            "canonicalization": FUSION_CANONICALIZATION,
            "purpose": purpose,
            "valueSchemaVersion": value_schema_version,
            "value": canonical_value,
        }
    )
    return _canonical_json(envelope).encode("utf-8")


def digest_canonical_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def equal_digest(expected: str, actual: str) -> bool:
    return (
        bool(re.fullmatch(r"sha256:[a-f0-9]{64}", expected))
        and bool(re.fullmatch(r"sha256:[a-f0-9]{64}", actual))
        and hmac.compare_digest(expected, actual)
    )


def project_semantic_request_for_digest(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value[key]
        for key in (
            "normalizedTopic",
            "normalizedLearningObjectives",
            "authorizedKnowledgeScope",
            "audienceSemantics",
            "teachingConstraints",
            "requestedKnowledgeRefs",
            "sourceMaterialRefs",
        )
    }


def compute_semantic_request_digest(value: dict[str, Any]) -> str:
    return digest_canonical_bytes(
        canonicalize_digest_envelope(
            "semantic-request",
            SEMANTIC_REQUEST_DIGEST_SCHEMA,
            project_semantic_request_for_digest(value),
        )
    )


def parse_lesson_semantic_request(value: Any) -> dict[str, Any]:
    item = _record(value)
    _fields(
        item,
        {
            "schemaVersion",
            "semanticRequestId",
            "semanticRequestRevision",
            "lessonSessionId",
            "semanticRequestDigest",
            "normalizedTopic",
            "normalizedLearningObjectives",
            "authorizedKnowledgeScope",
            "audienceSemantics",
            "teachingConstraints",
            "requestedKnowledgeRefs",
            "sourceMaterialRefs",
            "warnings",
        },
    )
    if item["schemaVersion"] != PRECLASS_CONTRACT_VERSION:
        _fail("unsupported_schema_version")
    scope, audience, constraints = (
        _record(item["authorizedKnowledgeScope"]),
        _record(item["audienceSemantics"]),
        _record(item["teachingConstraints"]),
    )
    _fields(scope, {"namespace", "scopeId", "allowedKnowledgeRefs"})
    _fields(audience, {"audienceType", "language"}, {"priorKnowledgeBand"})
    _fields(
        constraints, set(), {"durationMinutes", "maxSceneCount", "requiredModes", "prohibitedModes"}
    )
    result: dict[str, Any] = {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "semanticRequestId": _identifier(item["semanticRequestId"]),
        "semanticRequestRevision": _identifier(item["semanticRequestRevision"]),
        "lessonSessionId": _identifier(item["lessonSessionId"]),
        "semanticRequestDigest": _digest(item["semanticRequestDigest"]),
        "normalizedTopic": _text(item["normalizedTopic"]),
        "normalizedLearningObjectives": _string_array(item["normalizedLearningObjectives"]),
        "authorizedKnowledgeScope": {
            "namespace": _identifier(scope["namespace"]),
            "scopeId": _identifier(scope["scopeId"]),
            "allowedKnowledgeRefs": _refs(scope["allowedKnowledgeRefs"]),
        },
        "audienceSemantics": {
            "audienceType": _identifier(audience["audienceType"]),
            "language": _identifier(audience["language"]),
        },
        "teachingConstraints": {},
        "requestedKnowledgeRefs": _refs(item["requestedKnowledgeRefs"]),
        "sourceMaterialRefs": _materials(item["sourceMaterialRefs"]),
        "warnings": _string_array(item["warnings"]),
    }
    if "priorKnowledgeBand" in audience:
        result["audienceSemantics"]["priorKnowledgeBand"] = _identifier(
            audience["priorKnowledgeBand"]
        )
    if "durationMinutes" in constraints:
        result["teachingConstraints"]["durationMinutes"] = _integer(
            constraints["durationMinutes"], 600
        )
    if "maxSceneCount" in constraints:
        result["teachingConstraints"]["maxSceneCount"] = _integer(constraints["maxSceneCount"], 100)
    if "requiredModes" in constraints:
        result["teachingConstraints"]["requiredModes"] = _string_set(constraints["requiredModes"])
    if "prohibitedModes" in constraints:
        result["teachingConstraints"]["prohibitedModes"] = _string_set(
            constraints["prohibitedModes"]
        )
    allowed = {_ref_key(ref) for ref in result["authorizedKnowledgeScope"]["allowedKnowledgeRefs"]}
    if any(
        ref["namespace"] != result["authorizedKnowledgeScope"]["namespace"]
        or ref["scopeId"] != result["authorizedKnowledgeScope"]["scopeId"]
        or _ref_key(ref) not in allowed
        for ref in result["requestedKnowledgeRefs"]
    ):
        _fail("unauthorized_reference")
    if not equal_digest(result["semanticRequestDigest"], compute_semantic_request_digest(result)):
        _fail("digest_mismatch")
    return result


def _proposal(value: Any) -> dict[str, Any]:
    item = _record(value)
    required = {
        "schemaVersion",
        "proposalId",
        "basedOnSemanticRequestId",
        "basedOnSemanticRequestRevision",
        "semanticRequestDigest",
        "resolutionStatus",
        "interpretedLessonSemantics",
        "lessonKnowledgeMap",
        "learnerCognitiveProjection",
        "teachingGuidance",
        "sourceRevisions",
        "clarificationIssues",
        "warnings",
        "createdAt",
    }
    _fields(item, required)
    if item["schemaVersion"] != PRECLASS_CONTRACT_VERSION or item["resolutionStatus"] not in {
        "ready",
        "needs_clarification",
        "partial",
        "unresolved",
        "rejected",
    }:
        _fail("invalid_proposal")
    semantics, mapping, projection, guidance = (
        _record(item["interpretedLessonSemantics"]),
        _record(item["lessonKnowledgeMap"]),
        _record(item["learnerCognitiveProjection"]),
        _record(item["teachingGuidance"]),
    )
    _fields(semantics, {"normalizedTopic", "normalizedLearningObjectives"})
    _fields(mapping, {"mappingId", "mappingRevision", "knowledgeRefs"})
    _fields(projection, {"projectionRevision", "signals"})
    _fields(guidance, {"guidanceRevision", "recommendedApproaches"})
    return {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "proposalId": _identifier(item["proposalId"]),
        "basedOnSemanticRequestId": _identifier(item["basedOnSemanticRequestId"]),
        "basedOnSemanticRequestRevision": _identifier(item["basedOnSemanticRequestRevision"]),
        "semanticRequestDigest": _digest(item["semanticRequestDigest"]),
        "resolutionStatus": item["resolutionStatus"],
        "interpretedLessonSemantics": {
            "normalizedTopic": _text(semantics["normalizedTopic"]),
            "normalizedLearningObjectives": _string_array(
                semantics["normalizedLearningObjectives"]
            ),
        },
        "lessonKnowledgeMap": {
            "mappingId": _identifier(mapping["mappingId"]),
            "mappingRevision": _identifier(mapping["mappingRevision"]),
            "knowledgeRefs": _refs(mapping["knowledgeRefs"]),
        },
        "learnerCognitiveProjection": {
            "projectionRevision": _identifier(projection["projectionRevision"]),
            "signals": _string_array(projection["signals"]),
        },
        "teachingGuidance": {
            "guidanceRevision": _identifier(guidance["guidanceRevision"]),
            "recommendedApproaches": _string_array(guidance["recommendedApproaches"]),
        },
        "sourceRevisions": _string_array(item["sourceRevisions"]),
        "clarificationIssues": _string_array(item["clarificationIssues"]),
        "warnings": _string_array(item["warnings"]),
        "createdAt": _timestamp(item["createdAt"]),
    }


def parse_preclass_teaching_context_proposal(
    value: Any, request: dict[str, Any] | None = None
) -> dict[str, Any]:
    result = _proposal(value)
    if request and (
        result["basedOnSemanticRequestId"] != request["semanticRequestId"]
        or result["basedOnSemanticRequestRevision"] != request["semanticRequestRevision"]
        or not equal_digest(result["semanticRequestDigest"], request["semanticRequestDigest"])
    ):
        _fail("semantic_request_mismatch")
    return result


def parse_semantic_resolution(value: Any, request: dict[str, Any] | None = None) -> dict[str, Any]:
    item = _record(value)
    _fields(
        item,
        {
            "schemaVersion",
            "semanticRequestId",
            "semanticRequestRevision",
            "semanticRequestDigest",
            "status",
            "clarificationIssues",
        },
        {"reasonCode"},
    )
    if item["schemaVersion"] != PRECLASS_CONTRACT_VERSION or item["status"] not in {
        "ready",
        "needs_clarification",
        "partial",
        "unresolved",
        "rejected",
    }:
        _fail("invalid_resolution")
    result = {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "semanticRequestId": _identifier(item["semanticRequestId"]),
        "semanticRequestRevision": _identifier(item["semanticRequestRevision"]),
        "semanticRequestDigest": _digest(item["semanticRequestDigest"]),
        "status": item["status"],
        "clarificationIssues": _string_array(item["clarificationIssues"]),
    }
    if "reasonCode" in item:
        result["reasonCode"] = _identifier(item["reasonCode"])
    if request and (
        result["semanticRequestId"] != request["semanticRequestId"]
        or result["semanticRequestRevision"] != request["semanticRequestRevision"]
        or not equal_digest(result["semanticRequestDigest"], request["semanticRequestDigest"])
    ):
        _fail("semantic_request_mismatch")
    return result


def parse_frozen_lesson_generation_context(value: Any) -> dict[str, Any]:
    item = _record(value)
    _fields(
        item,
        {"schemaVersion", "contextId", "semanticRequest", "proposal", "resolution", "frozenAt"},
    )
    if item["schemaVersion"] != PRECLASS_CONTRACT_VERSION:
        _fail("unsupported_schema_version")
    request = parse_lesson_semantic_request(item["semanticRequest"])
    proposal = parse_preclass_teaching_context_proposal(item["proposal"], request)
    resolution = parse_semantic_resolution(item["resolution"], request)
    if proposal["resolutionStatus"] != "ready" or resolution["status"] != "ready":
        _fail("frozen_context_not_ready")
    return {
        "schemaVersion": PRECLASS_CONTRACT_VERSION,
        "contextId": _identifier(item["contextId"]),
        "semanticRequest": request,
        "proposal": proposal,
        "resolution": resolution,
        "frozenAt": _timestamp(item["frozenAt"]),
    }


def parse_strict_json(raw: str) -> Any:
    if not isinstance(raw, str) or len(raw) > 256 * 1024:
        _fail("payload_too_large")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        raw_keys: set[str] = set()
        for key, value in items:
            normalized = _text(key, 1_000_000)
            if key in raw_keys:
                _fail("duplicate_key")
            if normalized in result:
                _fail("normalized_key_collision")
            raw_keys.add(key)
            result[normalized] = value
        return result

    try:
        return _normalize(
            json.loads(
                raw, object_pairs_hook=pairs, parse_constant=lambda _value: _fail("invalid_json")
            )
        )
    except PreClassContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError):
        _fail("invalid_json")

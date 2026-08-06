from __future__ import annotations

import os
import secrets
import time

SCOPES = (
    "diagnosis:request",
    "classroom-event:write",
    "profile-update:submit",
    "preclass-context:read",
)
F24_SYNTHETIC_LEARNERS = ("f24-synthetic-a", "f24-synthetic-b")
_codes: dict[str, dict[str, object]] = {}
_revoked: set[str] = set()
_delegations: dict[str, dict[str, object]] = {}


def issue_launch_code(
    learner_id: str, course_scope: dict[str, object] | None = None
) -> str:
    code = secrets.token_urlsafe(32)
    _codes[code] = {
        "learnerId": learner_id,
        "expiresAt": time.time() + 300,
        **(
            {
                "courseScopeId": course_scope["courseScopeId"],
                "courseScopeRevision": course_scope["revision"],
            }
            if course_scope
            else {}
        ),
    }
    return code


def revoke_launch_code(code: str) -> None:
    _revoked.add(code)


def exchange_launch_code(
    code: str, audience: str, lesson_session_id: str
) -> dict[str, object] | None:
    record = _codes.pop(code, None)
    if (
        code in _revoked
        or not record
        or float(record["expiresAt"]) < time.time()
        or audience != "openmaic"
        or not lesson_session_id
    ):
        return None
    if record.get("courseScopeId"):
        from deeptutor.api.services.fusion_course_scope import (
            CourseScopeError,
            get_course_scope_registry,
        )

        try:
            get_course_scope_registry().bind_lesson(
                str(record["learnerId"]),
                lesson_session_id,
                str(record["courseScopeId"]),
                str(record["courseScopeRevision"]),
            )
        except CourseScopeError:
            return None
    result = {
        "token": secrets.token_urlsafe(32),
        "tokenId": secrets.token_hex(12),
        "learnerId": record["learnerId"],
        "audience": audience,
        "scope": list(SCOPES),
        "expiresAt": int(time.time() + 900),
        "lessonSessionId": lesson_session_id,
        **(
            {
                "courseScopeId": record["courseScopeId"],
                "courseScopeRevision": record["courseScopeRevision"],
            }
            if record.get("courseScopeId")
            else {}
        ),
    }
    _delegations[str(result["token"])] = result
    return result


def validate_delegation(token: str, scope: str, lesson_session_id: str) -> dict[str, object] | None:
    value = _delegations.get(token)
    return (
        value
        if value
        and value["audience"] == "openmaic"
        and scope in value["scope"]
        and value["lessonSessionId"] == lesson_session_id
        and int(value["expiresAt"]) > time.time()
        else None
    )


def validate_test_service_account(
    token: str, scope: str, lesson_session_id: str, learner_id: str
) -> bool:
    """Test-only, restricted worker identity bound to a previously launched learner/session."""
    configured = os.getenv("FUSION_TEST_SERVICE_ACCOUNT_TOKEN")
    if (
        os.getenv("ENVIRONMENT") != "test"
        or not configured
        or not secrets.compare_digest(token, configured)
    ):
        return False
    if scope not in ("classroom-event:write", "profile-update:submit"):
        return False
    delegation = next(
        (
            value
            for value in _delegations.values()
            if value["lessonSessionId"] == lesson_session_id
            and value["learnerId"] == learner_id
            and int(value["expiresAt"]) > time.time()
        ),
        None,
    )
    return delegation is not None

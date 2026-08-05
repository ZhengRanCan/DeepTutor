"""Delegation-protected F44 real pre-class semantic-context endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from deeptutor.api.services.fusion_course_scope import (
    CourseScopeError,
    get_course_scope_registry,
)
from deeptutor.api.services.fusion_delegation import validate_delegation
from deeptutor.api.services.fusion_preclass_context import (
    build_failed_proposal,
    build_real_proposal,
)
from deeptutor.fusion.preclass_contracts import (
    PreClassContractError,
    parse_lesson_semantic_request,
    parse_strict_json,
)
from deeptutor.multi_user.models import CurrentUser
from deeptutor.multi_user.paths import scope_for_user, user_context

router = APIRouter()
logger = logging.getLogger(__name__)
_MAX_PAYLOAD_BYTES = 256 * 1024
_SCOPE = "preclass-context:read"


def _credential(authorization: str | None, lesson_session_id: str) -> dict[str, object]:
    token = (authorization or "").removeprefix("Bearer ").strip()
    credential = validate_delegation(token, _SCOPE, lesson_session_id)
    if not credential:
        raise HTTPException(403, "delegation_invalid")
    return credential


@router.post("/pre-class/context")
async def pre_class_context(
    request: Request, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    """Return one strict proposal from the immutable launch-bound CourseScope."""
    raw = await request.body()
    if len(raw) > _MAX_PAYLOAD_BYTES:
        raise HTTPException(413, "payload_too_large")
    try:
        parsed = parse_lesson_semantic_request(parse_strict_json(raw.decode("utf-8")))
    except UnicodeDecodeError:
        raise HTTPException(400, "invalid_json") from None
    except PreClassContractError as error:
        raise HTTPException(400, error.code) from None
    credential = _credential(authorization, parsed["lessonSessionId"])
    learner_id = str(credential["learnerId"])
    try:
        binding = get_course_scope_registry().resolve_binding(
            learner_id, parsed["lessonSessionId"], require_active=True
        )
    except CourseScopeError as error:
        raise HTTPException(403, error.code) from None
    scope = parsed["authorizedKnowledgeScope"]
    if scope["namespace"] != "deeptutor" or scope["scopeId"] != binding["courseScopeId"]:
        raise HTTPException(403, "course_scope_mismatch")
    learner = CurrentUser(
        id=learner_id,
        username="fusion",
        role="user",
        scope=scope_for_user(learner_id, is_admin=False),
    )
    with user_context(learner):
        try:
            return build_real_proposal(parsed, binding)
        except Exception as error:
            logger.warning("Fusion pre-class decision pipeline failed: %s", type(error).__name__)
            return build_failed_proposal(parsed, binding, "decision_pipeline_unavailable")

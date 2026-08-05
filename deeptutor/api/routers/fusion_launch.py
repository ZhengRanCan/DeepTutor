import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from deeptutor.api.routers.auth import require_auth
from deeptutor.api.services.fusion_course_scope import CourseScopeError, get_course_scope_registry
from deeptutor.api.services.fusion_delegation import (
    exchange_launch_code,
    issue_launch_code,
    revoke_launch_code,
)
from deeptutor.multi_user.context import user_from_token_payload
from deeptutor.multi_user.paths import local_admin_user
from deeptutor.services.auth import TokenPayload

router = APIRouter()


class Exchange(BaseModel):
    code: str
    audience: str
    lessonSessionId: str


class LaunchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    courseScopeId: str | None = None


@router.post("/launch-codes")
async def issue(
    body: LaunchRequest | None = None,
    payload: TokenPayload | None = Depends(require_auth),
) -> dict[str, str]:
    environment = os.getenv("ENVIRONMENT", "development")
    allowed = set(filter(None, os.getenv("FUSION_TEST_USER_ALLOWLIST", "").split(",")))
    if environment == "production" and payload is None:
        raise HTTPException(403, "auth_required")
    learner_id = (
        payload.user_id
        if payload and payload.user_id
        else os.getenv("FUSION_DEVELOPMENT_LEARNER_ID", "")
    )
    if (
        not learner_id
        or (payload and learner_id not in allowed)
        or (
            payload is None
            and not (
                environment in {"development", "test"}
                and os.getenv("FUSION_DEVELOPMENT_MOCK_ENABLED") == "true"
            )
        )
    ):
        raise HTTPException(403, "launch_not_authorized")
    user = local_admin_user() if payload is None else user_from_token_payload(payload)
    if payload is not None and user.id != learner_id:
        raise HTTPException(403, "launch_identity_mismatch")
    try:
        scope = get_course_scope_registry().select_for_launch(
            learner_id, body.courseScopeId if body else None
        )
    except CourseScopeError as error:
        status = (
            409
            if error.code in {"course_scope_required", "course_scope_selection_required"}
            else 403
        )
        raise HTTPException(status, error.code) from None
    return {"classroomLaunchCode": issue_launch_code(learner_id, scope), "expiresInSeconds": "300"}


@router.delete("/launch-codes/{code}")
async def revoke(code: str, _: TokenPayload | None = Depends(require_auth)) -> dict[str, bool]:
    revoke_launch_code(code)
    return {"revoked": True}


@router.post("/launch/exchange")
async def exchange(body: Exchange) -> dict[str, object]:
    result = exchange_launch_code(body.code, body.audience, body.lessonSessionId)
    if not result:
        raise HTTPException(401, "invalid_launch_code")
    return result

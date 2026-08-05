"""Authenticated DeepTutor entry points for immutable CourseScope revisions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from deeptutor.api.routers.auth import require_auth
from deeptutor.api.services.fusion_course_scope import (
    CourseScopeError,
    get_course_scope_registry,
)
from deeptutor.book.storage import get_book_storage
from deeptutor.multi_user.context import user_from_token_payload
from deeptutor.multi_user.paths import local_admin_user, user_context
from deeptutor.services.auth import TokenPayload

router = APIRouter()


class CreateCourseScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bookIds: list[str] = Field(min_length=1, max_length=8)


def _user(payload: TokenPayload | None):
    return local_admin_user() if payload is None else user_from_token_payload(payload)


def _public(scope: dict[str, object]) -> dict[str, object]:
    return {
        key: scope[key]
        for key in ("courseScopeId", "revision", "bookIds", "status", "createdAt", "revokedAt")
    }


@router.post("/course-scopes")
async def create_course_scope(
    body: CreateCourseScope, payload: TokenPayload | None = Depends(require_auth)
) -> dict[str, object]:
    user = _user(payload)
    try:
        with user_context(user):
            scope = get_course_scope_registry().create_scope(
                user.id, body.bookIds, get_book_storage()
            )
    except CourseScopeError as error:
        raise HTTPException(400, error.code) from None
    return _public(scope)


@router.get("/course-scopes")
async def list_course_scopes(
    payload: TokenPayload | None = Depends(require_auth),
) -> dict[str, object]:
    user = _user(payload)
    try:
        scopes = get_course_scope_registry().active_scopes(user.id)
    except CourseScopeError as error:
        raise HTTPException(503, error.code) from None
    return {"items": [_public(scope) for scope in scopes]}


@router.delete("/course-scopes/{course_scope_id}")
async def revoke_course_scope(
    course_scope_id: str, payload: TokenPayload | None = Depends(require_auth)
) -> dict[str, object]:
    user = _user(payload)
    try:
        scope = get_course_scope_registry().revoke(user.id, course_scope_id)
    except CourseScopeError as error:
        raise HTTPException(404, error.code) from None
    return _public(scope)

"""Delegation-protected F41 pre-class semantic-context endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Request

from deeptutor.api.services.fusion_delegation import validate_delegation
from deeptutor.api.services.fusion_preclass_context import build_synthetic_proposal
from deeptutor.fusion.preclass_contracts import (
    PreClassContractError,
    parse_lesson_semantic_request,
    parse_strict_json,
)

router = APIRouter()
_MAX_PAYLOAD_BYTES = 256 * 1024
_SCOPE = "preclass-context:read"


def _credential(authorization: str | None, lesson_session_id: str) -> None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not validate_delegation(token, _SCOPE, lesson_session_id):
        raise HTTPException(403, "delegation_invalid")


@router.post("/pre-class/context")
async def pre_class_context(
    request: Request, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    """Return one strict, explicitly synthetic proposal for a delegated request."""
    if os.getenv("ENVIRONMENT", "development") not in {"development", "test"}:
        raise HTTPException(403, "synthetic_context_unavailable")
    raw = await request.body()
    if len(raw) > _MAX_PAYLOAD_BYTES:
        raise HTTPException(413, "payload_too_large")
    try:
        parsed = parse_lesson_semantic_request(parse_strict_json(raw.decode("utf-8")))
    except UnicodeDecodeError:
        raise HTTPException(400, "invalid_json") from None
    except PreClassContractError as error:
        raise HTTPException(400, error.code) from None
    _credential(authorization, parsed["lessonSessionId"])
    return build_synthetic_proposal(parsed)

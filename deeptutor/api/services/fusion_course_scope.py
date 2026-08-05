"""Persistent CourseScope and lesson-binding metadata for formal Fusion launch."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
from typing import Any
from uuid import uuid4

from deeptutor.book.storage import BookStorage
from deeptutor.multi_user import paths as multi_user_paths
from deeptutor.services.file_io import atomic_write_json

_SCHEMA_VERSION = "fusion-course-scope-registry-v1"
_WRITE_LOCK = threading.RLock()
_IDENTIFIER = re.compile(r"^[\x21-\x7e]{1,256}$")


class CourseScopeError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _identifier(value: object) -> str:
    result = str(value or "")
    if not _IDENTIFIER.fullmatch(result):
        raise CourseScopeError("invalid_course_scope")
    return result


class CourseScopeRegistry:
    """Small durable registry containing references only, never Book or learner content."""

    def __init__(self, path: Path | None = None):
        self.path = path or multi_user_paths.SYSTEM_ROOT / "fusion" / "course_scopes.json"

    def _empty(self) -> dict[str, Any]:
        return {"schemaVersion": _SCHEMA_VERSION, "scopes": [], "lessonBindings": []}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CourseScopeError("course_scope_store_unavailable") from error
        if (
            not isinstance(value, dict)
            or value.get("schemaVersion") != _SCHEMA_VERSION
            or not isinstance(value.get("scopes"), list)
            or not isinstance(value.get("lessonBindings"), list)
        ):
            raise CourseScopeError("course_scope_store_invalid")
        return value

    def _write(self, value: dict[str, Any]) -> None:
        atomic_write_json(self.path, value)

    def create_scope(
        self, learner_id: str, book_ids: list[str], storage: BookStorage
    ) -> dict[str, Any]:
        learner_id = _identifier(learner_id)
        normalized = sorted({_identifier(book_id) for book_id in book_ids})
        if not normalized or len(normalized) > 8 or len(normalized) != len(book_ids):
            raise CourseScopeError("invalid_book_roots")
        for book_id in normalized:
            book = storage.load_book(book_id)
            if book is None or str(getattr(book.status, "value", book.status)) == "archived":
                raise CourseScopeError("book_not_authorized")
        scope_id = f"course-{uuid4().hex}"
        digest = hashlib.sha256(
            json.dumps(
                {"learnerId": learner_id, "bookIds": normalized},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:20]
        created_at = _now()
        scope = {
            "courseScopeId": scope_id,
            "revision": f"r1-{digest}",
            "learnerId": learner_id,
            "bookIds": normalized,
            "status": "active",
            "createdAt": created_at,
            "revokedAt": None,
        }
        with _WRITE_LOCK:
            value = self._read()
            value["scopes"].append(scope)
            self._write(value)
        return dict(scope)

    def active_scopes(self, learner_id: str) -> list[dict[str, Any]]:
        learner_id = _identifier(learner_id)
        value = self._read()
        return [
            dict(scope)
            for scope in value["scopes"]
            if scope.get("learnerId") == learner_id and scope.get("status") == "active"
        ]

    def select_for_launch(self, learner_id: str, requested_scope_id: str | None) -> dict[str, Any]:
        active = self.active_scopes(learner_id)
        if requested_scope_id:
            requested_scope_id = _identifier(requested_scope_id)
            selected = next(
                (scope for scope in active if scope["courseScopeId"] == requested_scope_id), None
            )
            if selected is None:
                raise CourseScopeError("course_scope_not_available")
            return selected
        if not active:
            raise CourseScopeError("course_scope_required")
        if len(active) > 1:
            raise CourseScopeError("course_scope_selection_required")
        return active[0]

    def revoke(self, learner_id: str, scope_id: str) -> dict[str, Any]:
        learner_id, scope_id = _identifier(learner_id), _identifier(scope_id)
        with _WRITE_LOCK:
            value = self._read()
            scope = next(
                (
                    item
                    for item in value["scopes"]
                    if item.get("courseScopeId") == scope_id and item.get("learnerId") == learner_id
                ),
                None,
            )
            if scope is None:
                raise CourseScopeError("course_scope_not_available")
            if scope.get("status") == "active":
                scope["status"] = "revoked"
                scope["revokedAt"] = _now()
                self._write(value)
            return dict(scope)

    def bind_lesson(
        self,
        learner_id: str,
        lesson_session_id: str,
        course_scope_id: str,
        course_scope_revision: str,
    ) -> dict[str, Any]:
        learner_id = _identifier(learner_id)
        lesson_session_id = _identifier(lesson_session_id)
        course_scope_id = _identifier(course_scope_id)
        course_scope_revision = _identifier(course_scope_revision)
        with _WRITE_LOCK:
            value = self._read()
            scope = next(
                (
                    item
                    for item in value["scopes"]
                    if item.get("learnerId") == learner_id
                    and item.get("courseScopeId") == course_scope_id
                    and item.get("revision") == course_scope_revision
                    and item.get("status") == "active"
                ),
                None,
            )
            if scope is None:
                raise CourseScopeError("course_scope_not_available")
            existing = next(
                (
                    item
                    for item in value["lessonBindings"]
                    if item.get("lessonSessionId") == lesson_session_id
                ),
                None,
            )
            binding = {
                "lessonSessionId": lesson_session_id,
                "learnerId": learner_id,
                "courseScopeId": course_scope_id,
                "courseScopeRevision": course_scope_revision,
                "bookIds": list(scope["bookIds"]),
                "createdAt": _now(),
            }
            if existing:
                comparable = {key: existing.get(key) for key in binding if key != "createdAt"}
                expected = {key: binding[key] for key in binding if key != "createdAt"}
                if comparable != expected:
                    raise CourseScopeError("lesson_binding_conflict")
                return dict(existing)
            value["lessonBindings"].append(binding)
            self._write(value)
            return binding

    def resolve_binding(
        self, learner_id: str, lesson_session_id: str, *, require_active: bool = True
    ) -> dict[str, Any]:
        learner_id, lesson_session_id = _identifier(learner_id), _identifier(lesson_session_id)
        value = self._read()
        binding = next(
            (
                item
                for item in value["lessonBindings"]
                if item.get("learnerId") == learner_id
                and item.get("lessonSessionId") == lesson_session_id
            ),
            None,
        )
        if binding is None:
            raise CourseScopeError("lesson_binding_not_found")
        scope = next(
            (
                item
                for item in value["scopes"]
                if item.get("learnerId") == learner_id
                and item.get("courseScopeId") == binding.get("courseScopeId")
                and item.get("revision") == binding.get("courseScopeRevision")
            ),
            None,
        )
        if scope is None or (require_active and scope.get("status") != "active"):
            raise CourseScopeError("course_scope_revoked")
        return dict(binding)


def get_course_scope_registry() -> CourseScopeRegistry:
    return CourseScopeRegistry()


__all__ = ["CourseScopeError", "CourseScopeRegistry", "get_course_scope_registry"]

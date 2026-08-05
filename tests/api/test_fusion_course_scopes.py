from __future__ import annotations

import pytest

from deeptutor.api.services.fusion_course_scope import CourseScopeError, CourseScopeRegistry
from deeptutor.book.models import Book, BookStatus


class FakeBookStorage:
    def __init__(self, book_ids: set[str]):
        self.book_ids = book_ids

    def load_book(self, book_id: str):
        return (
            Book(id=book_id, title=book_id, status=BookStatus.READY)
            if book_id in self.book_ids
            else None
        )


def test_scope_selection_binding_revision_and_revoke(tmp_path) -> None:
    registry = CourseScopeRegistry(tmp_path / "registry.json")
    storage = FakeBookStorage({"book-a", "book-b"})
    with pytest.raises(CourseScopeError, match="course_scope_required"):
        registry.select_for_launch("learner-1", None)
    first = registry.create_scope("learner-1", ["book-a"], storage)  # type: ignore[arg-type]
    assert registry.select_for_launch("learner-1", None)["courseScopeId"] == first["courseScopeId"]

    second = registry.create_scope("learner-1", ["book-b"], storage)  # type: ignore[arg-type]
    with pytest.raises(CourseScopeError, match="course_scope_selection_required"):
        registry.select_for_launch("learner-1", None)
    selected = registry.select_for_launch("learner-1", str(first["courseScopeId"]))
    binding = registry.bind_lesson(
        "learner-1", "lesson-1", str(selected["courseScopeId"]), str(selected["revision"])
    )
    assert binding["bookIds"] == ["book-a"]
    assert (
        registry.resolve_binding("learner-1", "lesson-1")["courseScopeRevision"]
        == first["revision"]
    )

    registry.revoke("learner-1", str(first["courseScopeId"]))
    with pytest.raises(CourseScopeError, match="course_scope_revoked"):
        registry.resolve_binding("learner-1", "lesson-1")
    assert registry.select_for_launch("learner-1", None)["courseScopeId"] == second["courseScopeId"]


def test_scope_rejects_missing_or_duplicate_book_roots(tmp_path) -> None:
    registry = CourseScopeRegistry(tmp_path / "registry.json")
    storage = FakeBookStorage({"book-a"})
    with pytest.raises(CourseScopeError, match="book_not_authorized"):
        registry.create_scope("learner-1", ["missing"], storage)  # type: ignore[arg-type]
    with pytest.raises(CourseScopeError, match="invalid_book_roots"):
        registry.create_scope("learner-1", ["book-a", "book-a"], storage)  # type: ignore[arg-type]

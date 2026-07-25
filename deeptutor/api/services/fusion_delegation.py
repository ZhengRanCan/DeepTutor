from __future__ import annotations
import secrets, time
from dataclasses import dataclass

SCOPES = ('profile:read', 'diagnosis:request', 'classroom-event:write', 'profile-update:submit')
_codes: dict[str, tuple[str, float]] = {}
_revoked: set[str] = set()

def issue_launch_code(learner_id: str) -> str:
    code = secrets.token_urlsafe(32); _codes[code] = (learner_id, time.time() + 300); return code
def revoke_launch_code(code: str) -> None: _revoked.add(code)
def exchange_launch_code(code: str, audience: str, lesson_session_id: str) -> dict[str, object] | None:
    record = _codes.pop(code, None)
    if code in _revoked or not record or record[1] < time.time() or audience != 'openmaic' or not lesson_session_id: return None
    return {'token': secrets.token_urlsafe(32), 'tokenId': secrets.token_hex(12), 'learnerId': record[0], 'audience': audience, 'scope': list(SCOPES), 'expiresAt': int(time.time() + 900), 'lessonSessionId': lesson_session_id}

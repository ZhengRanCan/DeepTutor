from __future__ import annotations
import os, secrets, time
from dataclasses import dataclass

SCOPES = ('profile:read', 'diagnosis:request', 'classroom-event:write', 'profile-update:submit')
_codes: dict[str, tuple[str, float]] = {}
_revoked: set[str] = set()
_delegations: dict[str, dict[str, object]] = {}

def issue_launch_code(learner_id: str) -> str:
    code = secrets.token_urlsafe(32); _codes[code] = (learner_id, time.time() + 300); return code
def revoke_launch_code(code: str) -> None: _revoked.add(code)
def exchange_launch_code(code: str, audience: str, lesson_session_id: str) -> dict[str, object] | None:
    record = _codes.pop(code, None)
    if code in _revoked or not record or record[1] < time.time() or audience != 'openmaic' or not lesson_session_id: return None
    result={'token': secrets.token_urlsafe(32), 'tokenId': secrets.token_hex(12), 'learnerId': record[0], 'audience': audience, 'scope': list(SCOPES), 'expiresAt': int(time.time() + 900), 'lessonSessionId': lesson_session_id}; _delegations[str(result['token'])]=result; return result
def validate_delegation(token: str, scope: str, lesson_session_id: str) -> dict[str, object] | None:
    value=_delegations.get(token); return value if value and value['audience']=='openmaic' and scope in value['scope'] and value['lessonSessionId']==lesson_session_id and int(value['expiresAt'])>time.time() else None

def validate_test_service_account(token: str, scope: str, lesson_session_id: str, learner_id: str) -> bool:
    """Test-only, restricted worker identity bound to a previously launched learner/session."""
    configured = os.getenv('FUSION_TEST_SERVICE_ACCOUNT_TOKEN')
    if os.getenv('ENVIRONMENT') != 'test' or not configured or not secrets.compare_digest(token, configured):
        return False
    if scope not in ('classroom-event:write', 'profile-update:submit'):
        return False
    delegation = next(
        (
            value for value in _delegations.values()
            if value['lessonSessionId'] == lesson_session_id
            and value['learnerId'] == learner_id
            and int(value['expiresAt']) > time.time()
        ),
        None,
    )
    return delegation is not None

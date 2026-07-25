import deeptutor.api.services.fusion_delegation as delegation
from deeptutor.api.services.fusion_delegation import SCOPES, exchange_launch_code, issue_launch_code, revoke_launch_code
def test_launch_code_is_one_time_and_audience_bound():
 code=issue_launch_code('learner-1'); first=exchange_launch_code(code,'openmaic','lesson-1'); assert first and first['learnerId']=='learner-1' and 'profile:read' in first['scope']; assert exchange_launch_code(code,'openmaic','lesson-1') is None
def test_wrong_audience_rejects_code(): assert exchange_launch_code(issue_launch_code('learner-1'),'wrong','lesson-1') is None
def test_revoked_code_rejects_exchange():
 code=issue_launch_code('learner-1'); revoke_launch_code(code); assert exchange_launch_code(code,'openmaic','lesson-1') is None
def test_expired_code_and_session_binding_reject(monkeypatch):
 code=issue_launch_code('learner-1'); monkeypatch.setattr(delegation.time,'time',lambda: 9_999_999_999); assert exchange_launch_code(code,'openmaic','lesson-1') is None
def test_exchange_has_exact_minimum_scope_and_session_binding():
 result=exchange_launch_code(issue_launch_code('learner-1'),'openmaic','lesson-1'); assert result and tuple(result['scope'])==SCOPES and result['lessonSessionId']=='lesson-1' and result['audience']=='openmaic'

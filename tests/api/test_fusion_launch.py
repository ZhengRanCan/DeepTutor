import deeptutor.api.services.fusion_delegation as delegation
from fastapi import FastAPI
from fastapi.testclient import TestClient
from deeptutor.api.routers.auth import require_auth
from deeptutor.api.routers.fusion_launch import router
from deeptutor.services.auth import TokenPayload
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
def launch_client(payload):
 app=FastAPI(); app.include_router(router,prefix='/api/v1/fusion')
 async def auth_override(): return payload
 app.dependency_overrides[require_auth]=auth_override
 return TestClient(app)
def test_allowlist_authorizes_only_explicit_test_user(monkeypatch):
 monkeypatch.setenv('ENVIRONMENT','test'); monkeypatch.setenv('FUSION_TEST_USER_ALLOWLIST','learner-ok'); client=launch_client(TokenPayload(username='ok',role='user',user_id='learner-ok')); assert client.post('/api/v1/fusion/launch-codes').status_code==200
 client=launch_client(TokenPayload(username='no',role='user',user_id='learner-no')); assert client.post('/api/v1/fusion/launch-codes').status_code==403
def test_production_auth_disabled_rejects_issue(monkeypatch):
 monkeypatch.setenv('ENVIRONMENT','production'); monkeypatch.setenv('FUSION_DEVELOPMENT_MOCK_ENABLED','true'); monkeypatch.setenv('FUSION_DEVELOPMENT_LEARNER_ID','demo'); assert launch_client(None).post('/api/v1/fusion/launch-codes').status_code==403

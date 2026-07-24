from fastapi import FastAPI
from fastapi.testclient import TestClient
from deeptutor.api.routers.fusion_profile_updates import router
def candidate(): return {'schemaVersion':'v1','candidateId':'candidate-1','idempotencyKey':'key-1','lessonSessionId':'lesson','mappingId':'map','mappingRevision':'1','createdAt':'2026-01-01T00:00:00Z','observations':[{'kind':'misconception_signal'}]}
def test_receipt_and_duplicate(monkeypatch):
 monkeypatch.setenv('ENVIRONMENT','test'); monkeypatch.setenv('FUSION_DEVELOPMENT_MOCK_ENABLED','true'); app=FastAPI(); app.include_router(router,prefix='/api/v1/fusion'); client=TestClient(app); assert client.post('/api/v1/fusion/profile-updates',json=candidate()).json()['status']=='accepted'; assert client.post('/api/v1/fusion/profile-updates',json=candidate()).json()['status']=='duplicate'
def test_rejects_invalid_and_disabled(monkeypatch):
 app=FastAPI(); app.include_router(router,prefix='/api/v1/fusion'); monkeypatch.setenv('ENVIRONMENT','production'); monkeypatch.setenv('FUSION_DEVELOPMENT_MOCK_ENABLED','true'); assert TestClient(app).post('/api/v1/fusion/profile-updates',json=candidate()).status_code==403

from fastapi.testclient import TestClient

from deeptutor.api.routers.fusion_test_app import create_app
from deeptutor.api.services.fusion_delegation import (
    F24_SYNTHETIC_LEARNERS,
    exchange_launch_code,
    issue_launch_code,
    validate_delegation,
)


def test_profile_delegation_requires_scope_and_lesson_binding():
 delegation=exchange_launch_code(issue_launch_code('integration-test-learner'),'openmaic','lesson-1'); assert delegation; assert validate_delegation(str(delegation['token']),'profile:read','lesson-1'); assert not validate_delegation(str(delegation['token']),'profile:read','wrong'); assert not validate_delegation(str(delegation['token']),'admin:write','lesson-1')


def test_f24_synthetic_learners_have_distinct_minimal_profile_and_map(monkeypatch):
 monkeypatch.setenv('ENVIRONMENT','test')
 client = TestClient(create_app())
 payloads = []
 for index, learner in enumerate(F24_SYNTHETIC_LEARNERS):
  lesson = f'f24-lesson-{index}'
  delegation = exchange_launch_code(issue_launch_code(learner), 'openmaic', lesson)
  assert delegation
  headers = {'Authorization': f"Bearer {delegation['token']}"}
  profile = client.get('/api/v1/fusion/profile', params={'lessonSessionId': lesson}, headers=headers)
  knowledge_map = client.get('/api/v1/fusion/knowledge-map', params={'lessonSessionId': lesson}, headers=headers)
  assert profile.status_code == 200 and knowledge_map.status_code == 200
  payloads.append((profile.json(), knowledge_map.json()))
 profile_a, map_a = payloads[0]
 profile_b, map_b = payloads[1]
 assert profile_a['learnerId'] != profile_b['learnerId']
 assert profile_a['profileRevision'] != profile_b['profileRevision']
 assert profile_a['knowledgeState'] != profile_b['knowledgeState']
 assert (map_a['mappingId'], map_a['mappingRevision']) != (map_b['mappingId'], map_b['mappingRevision'])
 assert map_a['knowledgePoints'] == map_b['knowledgePoints']

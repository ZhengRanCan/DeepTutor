from fastapi import APIRouter, Header, HTTPException, Query
from deeptutor.api.services.fusion_delegation import validate_delegation
router=APIRouter()
_PROFILES = {
 'integration-test-learner': ('integration-test-v1', 'integration-test-map', '1', 'insufficient_data', 0.0),
 'allowlisted-synthetic-learner': ('integration-test-v1', 'integration-test-map', '1', 'insufficient_data', 0.0),
 'f24-synthetic-a': ('f24-synthetic-a-v1', 'f24-map-a', '1', 'insufficient_data', 0.0),
 'f24-synthetic-b': ('f24-synthetic-b-v1', 'f24-map-b', '2', 'observed', 0.9),
}
def credential(authorization: str|None, scope:str, lesson_session_id:str):
 token=(authorization or '').removeprefix('Bearer ').strip(); value=validate_delegation(token,scope,lesson_session_id)
 if not value: raise HTTPException(403,'delegation_invalid')
 return value
def profile_fixture(learner_id: str):
 value = _PROFILES.get(learner_id)
 if not value: raise HTTPException(404,'synthetic_profile_not_configured')
 return value
@router.get('/profile')
async def profile(lessonSessionId:str=Query(),authorization:str|None=Header(default=None)):
 value=credential(authorization,'profile:read',lessonSessionId)
 profile_revision, _, _, data_status, confidence = profile_fixture(str(value['learnerId']))
 return {'schemaVersion':'v1','profileRevision':profile_revision,'learnerId':value['learnerId'],'knowledgeState':[{'lessonKnowledgePointId':'lesson-linear-function-slope','name':'Linear function slope','dataStatus':data_status,'confidence':confidence}],'strengths':[],'weakPoints':[],'warnings':['integration_test_identity_only'],'updatedAt':'2026-07-25T00:00:00Z'}
@router.get('/knowledge-map')
async def knowledge_map(lessonSessionId:str=Query(),authorization:str|None=Header(default=None)):
 value=credential(authorization,'profile:read',lessonSessionId)
 _, mapping_id, mapping_revision, _, _ = profile_fixture(str(value['learnerId']))
 return {'schemaVersion':'v1','mappingId':mapping_id,'mappingRevision':mapping_revision,'knowledgePoints':[{'lessonKnowledgePointId':'lesson-linear-function-slope','mappingStatus':'mapped','authoritativeRef':{'namespace':'integration-test','scopeId':'linear-function','id':'slope'}}],'warnings':[]}

from fastapi import APIRouter, Header, HTTPException, Query
from deeptutor.api.services.fusion_delegation import validate_delegation
router=APIRouter()
def credential(authorization: str|None, scope:str, lesson_session_id:str):
 token=(authorization or '').removeprefix('Bearer ').strip(); value=validate_delegation(token,scope,lesson_session_id)
 if not value: raise HTTPException(403,'delegation_invalid')
 return value
@router.get('/profile')
async def profile(lessonSessionId:str=Query(),authorization:str|None=Header(default=None)):
 value=credential(authorization,'profile:read',lessonSessionId)
 return {'schemaVersion':'v1','profileRevision':'integration-test-v1','learnerId':value['learnerId'],'knowledgeState':[{'lessonKnowledgePointId':'lesson-linear-function-slope','name':'Linear function slope','dataStatus':'insufficient_data','confidence':0.0}],'strengths':[],'weakPoints':[],'warnings':['integration_test_identity_only'],'updatedAt':'2026-07-25T00:00:00Z'}
@router.get('/knowledge-map')
async def knowledge_map(lessonSessionId:str=Query(),authorization:str|None=Header(default=None)):
 credential(authorization,'profile:read',lessonSessionId); return {'schemaVersion':'v1','mappingId':'integration-test-map','mappingRevision':'1','knowledgePoints':[{'lessonKnowledgePointId':'lesson-linear-function-slope','mappingStatus':'mapped','authoritativeRef':{'namespace':'integration-test','scopeId':'linear-function','id':'slope'}}],'warnings':[]}

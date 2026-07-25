from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from deeptutor.api.routers.auth import require_auth
from deeptutor.services.auth import TokenPayload
import os
from deeptutor.api.services.fusion_delegation import issue_launch_code, exchange_launch_code, revoke_launch_code
router = APIRouter()
class Exchange(BaseModel): code: str; audience: str; lessonSessionId: str
@router.post('/launch-codes')
async def issue(payload: TokenPayload | None = Depends(require_auth)) -> dict[str, str]:
    environment=os.getenv('ENVIRONMENT','development'); allowed=set(filter(None,os.getenv('FUSION_TEST_USER_ALLOWLIST','').split(',')))
    if environment == 'production' and payload is None: raise HTTPException(403,'auth_required')
    learner_id = payload.user_id if payload and payload.user_id else os.getenv('FUSION_DEVELOPMENT_LEARNER_ID','')
    if not learner_id or (payload and learner_id not in allowed) or (payload is None and not (environment in {'development','test'} and os.getenv('FUSION_DEVELOPMENT_MOCK_ENABLED') == 'true')): raise HTTPException(403,'launch_not_authorized')
    return {'classroomLaunchCode': issue_launch_code(learner_id), 'expiresInSeconds': '300'}
@router.delete('/launch-codes/{code}')
async def revoke(code: str, _: TokenPayload | None = Depends(require_auth)) -> dict[str,bool]: revoke_launch_code(code); return {'revoked':True}
@router.post('/launch/exchange')
async def exchange(body: Exchange) -> dict[str, object]:
    result = exchange_launch_code(body.code, body.audience, body.lessonSessionId)
    if not result: raise HTTPException(401, 'invalid_launch_code')
    return result

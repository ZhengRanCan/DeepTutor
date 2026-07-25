from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from deeptutor.api.routers.auth import require_auth
from deeptutor.services.auth import TokenPayload
from deeptutor.api.services.fusion_delegation import issue_launch_code, exchange_launch_code
router = APIRouter()
class Exchange(BaseModel): code: str; audience: str; lessonSessionId: str
@router.post('/launch-codes')
async def issue(payload: TokenPayload | None = Depends(require_auth)) -> dict[str, str]:
    learner_id = payload.user_id if payload and payload.user_id else 'local-admin'
    return {'classroomLaunchCode': issue_launch_code(learner_id), 'expiresInSeconds': '300'}
@router.post('/launch/exchange')
async def exchange(body: Exchange) -> dict[str, object]:
    result = exchange_launch_code(body.code, body.audience, body.lessonSessionId)
    if not result: raise HTTPException(401, 'invalid_launch_code')
    return result

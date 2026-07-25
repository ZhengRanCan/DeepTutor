import os
from fastapi import APIRouter, HTTPException, Header
from deeptutor.api.services.fusion_profile_updates import receive_candidate
from deeptutor.api.services.fusion_delegation import validate_delegation
router = APIRouter()
@router.post('/profile-updates')
async def profile_update(candidate: dict[str, object]) -> dict[str, str]:
    if os.getenv('FUSION_DEVELOPMENT_MOCK_ENABLED') != 'true' or os.getenv('ENVIRONMENT') not in {'development', 'test'}: raise HTTPException(403, 'development_mock_disabled')
    return receive_candidate(candidate)
@router.post('/real-profile-updates')
async def real_profile_update(candidate: dict[str, object], authorization: str|None=Header(default=None)) -> dict[str,str]:
 token=(authorization or '').removeprefix('Bearer ').strip()
 if not validate_delegation(token,'profile-update:submit',str(candidate.get('lessonSessionId',''))): raise HTTPException(403,'delegation_invalid')
 return receive_candidate(candidate)

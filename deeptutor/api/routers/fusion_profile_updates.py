import os
from fastapi import APIRouter, HTTPException
from deeptutor.api.services.fusion_profile_updates import receive_candidate
router = APIRouter()
@router.post('/profile-updates')
async def profile_update(candidate: dict[str, object]) -> dict[str, str]:
    if os.getenv('FUSION_DEVELOPMENT_MOCK_ENABLED') != 'true' or os.getenv('ENVIRONMENT') not in {'development', 'test'}: raise HTTPException(403, 'development_mock_disabled')
    return receive_candidate(candidate)

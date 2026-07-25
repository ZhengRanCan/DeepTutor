import os
from fastapi import APIRouter, HTTPException, Header
from deeptutor.api.services.fusion_diagnosis import FusionDiagnosisError, diagnose_checkpoint
from deeptutor.api.services.fusion_delegation import validate_delegation

router = APIRouter()

@router.post("/diagnosis")
async def diagnose(event: dict[str, object]) -> dict[str, object]:
    if os.getenv("FUSION_DEVELOPMENT_MOCK_ENABLED") != "true" or os.getenv("ENVIRONMENT") not in {"development", "test"}:
        raise HTTPException(status_code=403, detail="development_mock_disabled")
    try:
        return diagnose_checkpoint(event)
    except FusionDiagnosisError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post('/real-diagnosis')
async def real_diagnose(event: dict[str, object], authorization: str|None=Header(default=None)) -> dict[str, object]:
    token=(authorization or '').removeprefix('Bearer ').strip(); lesson=str(event.get('lessonSessionId',''))
    if not validate_delegation(token,'diagnosis:request',lesson): raise HTTPException(403,'delegation_invalid')
    try: return diagnose_checkpoint(event)
    except FusionDiagnosisError as error: raise HTTPException(422,str(error)) from error

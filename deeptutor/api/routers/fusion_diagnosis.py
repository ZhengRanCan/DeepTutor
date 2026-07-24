import os
from fastapi import APIRouter, HTTPException
from deeptutor.api.services.fusion_diagnosis import FusionDiagnosisError, diagnose_checkpoint

router = APIRouter()

@router.post("/diagnosis")
async def diagnose(event: dict[str, object]) -> dict[str, object]:
    if os.getenv("FUSION_DEVELOPMENT_MOCK_ENABLED") != "true" or os.getenv("ENVIRONMENT") not in {"development", "test"}:
        raise HTTPException(status_code=403, detail="development_mock_disabled")
    try:
        return diagnose_checkpoint(event)
    except FusionDiagnosisError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

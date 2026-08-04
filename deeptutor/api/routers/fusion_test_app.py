"""Isolated, test-only Fusion API host for local integration demonstrations."""

import os

from fastapi import FastAPI

from deeptutor.api.routers.fusion_diagnosis import router as diagnosis_router
from deeptutor.api.routers.fusion_launch import router as launch_router
from deeptutor.api.routers.fusion_profile import router as profile_router
from deeptutor.api.routers.fusion_profile_updates import router as profile_updates_router
from deeptutor.api.routers.fusion_preclass_context import router as preclass_context_router


def create_app() -> FastAPI:
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("The isolated Fusion app is available only when ENVIRONMENT=test")
    app = FastAPI()
    for router in (
        launch_router,
        profile_router,
        diagnosis_router,
        profile_updates_router,
        preclass_context_router,
    ):
        app.include_router(router, prefix="/api/v1/fusion")
    return app

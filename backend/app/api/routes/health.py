from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthCheckResponse)
async def health_check(settings: Annotated[Settings, Depends(get_settings)]) -> HealthCheckResponse:
    return HealthCheckResponse(status="ok", service=settings.app_name)

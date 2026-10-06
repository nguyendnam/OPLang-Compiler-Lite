from typing import Annotated

from fastapi import APIRouter, Depends, Response

from backend.app.schemas import HealthResponse
from backend.app.services.compiler_service import CompilerService, get_compiler_service

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(
    response: Response,
    service: Annotated[CompilerService, Depends(get_compiler_service)],
) -> HealthResponse:
    available = service.is_available()
    if not available:
        response.status_code = 503
    return HealthResponse(
        status="healthy" if available else "unavailable",
        compilerVersion="0.1.0",
        compilerCoreInstalled=available,
    )

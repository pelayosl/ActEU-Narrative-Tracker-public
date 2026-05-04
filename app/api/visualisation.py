from fastapi import APIRouter, Depends

from app.api.dependencies import get_visualisation_service
from app.schemas.visualisation import Dashboard, VisualisationQuery
from app.services.visualisation_service import VisualisationService

router = APIRouter(prefix="/visualisation", tags=["visualisation"])


@router.post("/", response_model=Dashboard)
async def load_dashboard(
    query: VisualisationQuery,
    service: VisualisationService = Depends(get_visualisation_service),
) -> Dashboard:
    raise NotImplementedError

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.api import (
    auth,
    classification,
    jobs,
    projects,
    search,
    topics,
    visualisation,
)

app = FastAPI(title="ActEU Narrative Tracker", redirect_slashes=False)


@app.exception_handler(PyMongoError)
async def database_unavailable_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    """Translate any MongoDB driver error (connection refused, server selection
    timeout, etc.) into a clear 503 so the frontend can tell the user the database
    is unavailable instead of showing a generic failure. Domain exceptions are still
    handled per-route; this is the infrastructure-level safety net."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The database is currently unavailable. Please try again later."},
    )

app.include_router(search.router)
app.include_router(projects.router)
app.include_router(topics.router)
app.include_router(classification.router)
app.include_router(visualisation.router)
app.include_router(jobs.router)
app.include_router(auth.router)

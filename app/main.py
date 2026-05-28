from fastapi import FastAPI

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

app.include_router(search.router)
app.include_router(projects.router)
app.include_router(topics.router)
app.include_router(classification.router)
app.include_router(visualisation.router)
app.include_router(jobs.router)
app.include_router(auth.router)

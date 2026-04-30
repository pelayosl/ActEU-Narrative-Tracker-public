from fastapi import FastAPI

from app.api import (
    auth,
    classification,
    jobs,
    search,
    topics,
    visualisation,
)

app = FastAPI(title="ActEU Narrative Tracker")

app.include_router(search.router)
app.include_router(topics.router)
app.include_router(classification.router)
app.include_router(visualisation.router)
app.include_router(jobs.router)
app.include_router(auth.router)

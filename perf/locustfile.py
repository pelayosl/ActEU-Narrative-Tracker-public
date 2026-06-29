"""Locust load-testing harness for the ActEU Narrative Tracker.

Drives the FastAPI gateway **directly** (the chosen load target) with two user types
that mirror the two operation groups of the timing study:

* :class:`SearchVisualisationUser` — read-only, user-facing traffic (search,
  visualisation, language facet). The high-concurrency group.
* :class:`PipelineUser` — concurrent pipeline submissions (Phase 2 labelling and/or
  topic generation). The low-concurrency, heavy group that stresses the Celery queue
  and the per-project Redis labelling mutex. A ``409`` mutex rejection is treated as a
  **successful graceful degradation**, not a failure.

Configuration is entirely via environment variables (see ``perf/README.md``):

    LOCUST_USERNAME / LOCUST_PASSWORD   credentials used to obtain a JWT (required)
    LOCUST_PROJECT_ID                   project scope for the pipeline user (optional)
    LOCUST_CLASSIFIER_ID                classifier for Phase 2 labelling (optional)
    LOCUST_DOC_IDS                      comma-separated doc_ids for topic generation
                                        (optional; needs >= 10 to produce topics)

``PipelineUser`` only spawns when at least one of its operations is configured; the
read group always works out of the box.

Run (read group only):
    locust -f perf/locustfile.py --host https://<host> SearchVisualisationUser

Run (both groups, headless ramp):
    locust -f perf/locustfile.py --host https://<host> \
        --headless -u 25 -r 5 -t 5m --csv perf/results/run1
"""

import os
import random
from datetime import datetime, timezone

from locust import HttpUser, between, task

# --- Static facet pools (match the dataset / core schema) --------------------
CORE_TOPICS = ["immigration", "climate_change", "gender_issues"]
LANGUAGES = ["en", "es", "fr", "de", "it", "pl", "nl", "sv", "hu", "pt", "el"]
PLATFORMS = ["twitter", "telegram", "media"]
KEYWORD_POOL = ["border", "energy", "rights", "policy", "protest", "election", "law"]

DATE_FROM = datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat()
DATE_TO = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()

# --- Pipeline configuration (optional) ---------------------------------------
PROJECT_ID = os.getenv("LOCUST_PROJECT_ID", "").strip()
CLASSIFIER_ID = os.getenv("LOCUST_CLASSIFIER_ID", "").strip()
DOC_IDS = [d for d in os.getenv("LOCUST_DOC_IDS", "").split(",") if d.strip()]

LABELLING_ENABLED = bool(PROJECT_ID and CLASSIFIER_ID)
GENERATION_ENABLED = bool(PROJECT_ID and len(DOC_IDS) >= 10)
PIPELINE_ENABLED = LABELLING_ENABLED or GENERATION_ENABLED


def _login(client) -> bool:
    """Obtain a JWT and set it as the default bearer header on the client.

    :returns: True if authentication succeeded.
    """
    username = os.getenv("LOCUST_USERNAME", "")
    password = os.getenv("LOCUST_PASSWORD", "")
    with client.post(
        "/auth/login",
        json={"username": username, "password": password},
        name="POST /auth/login",
        catch_response=True,
    ) as response:
        if response.status_code != 200:
            response.failure(f"login failed: {response.status_code} {response.text[:120]}")
            return False
        token = response.json().get("access_token")
        if not token:
            response.failure("login response carried no access_token")
            return False
        client.headers["Authorization"] = f"Bearer {token}"
        return True


def _random_search_body() -> dict:
    """A realistic, randomised faceted search payload."""
    return {
        "keywords": random.sample(KEYWORD_POOL, k=random.randint(0, 2)),
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "languages": random.sample(LANGUAGES, k=random.randint(0, 3)),
        "platforms": random.sample(PLATFORMS, k=random.randint(0, 2)),
        "topics": random.sample(CORE_TOPICS, k=random.randint(1, 3)),
        "subtopics": [],
        "confidence_threshold": random.choice([None, 0.5, 0.7]),
    }


def _random_visualisation_body() -> dict:
    """A realistic visualisation query (topics and date range are required)."""
    return {
        "topics": random.sample(CORE_TOPICS, k=random.randint(1, 3)),
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "languages": random.sample(LANGUAGES, k=random.randint(0, 3)),
        "platforms": random.sample(PLATFORMS, k=random.randint(0, 2)),
        "sample_size": random.choice([10, 30, 50]),
    }


class SearchVisualisationUser(HttpUser):
    """User-facing read traffic: search, visualisation and the language facet."""

    weight = 4
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.authenticated = _login(self.client)

    @task(3)
    def search(self) -> None:
        if not getattr(self, "authenticated", False):
            return
        self.client.post("/search/", json=_random_search_body(), name="POST /search/")

    @task(2)
    def visualisation(self) -> None:
        if not getattr(self, "authenticated", False):
            return
        self.client.post(
            "/visualisation/", json=_random_visualisation_body(), name="POST /visualisation/"
        )

    @task(1)
    def languages(self) -> None:
        if not getattr(self, "authenticated", False):
            return
        self.client.get("/search/languages", name="GET /search/languages")


class PipelineUser(HttpUser):
    """Concurrent pipeline submissions: stresses the Celery queue and the labelling mutex.

    Only spawns when configured (``weight = 0`` disables a user class entirely).
    """

    weight = 1 if PIPELINE_ENABLED else 0
    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.authenticated = _login(self.client)

    @task(3)
    def submit_labelling(self) -> None:
        """Phase 2 labelling — the per-project Redis mutex contention point.

        Concurrent submissions on the same project should return ``409 LabellingLocked``;
        that is the *expected* graceful outcome and is recorded as a success.
        """
        if not LABELLING_ENABLED or not getattr(self, "authenticated", False):
            return
        body = {
            "project_id": PROJECT_ID,
            "classifier_id": CLASSIFIER_ID,
            "query": _random_search_body(),
        }
        with self.client.post(
            "/classification/label", json=body, name="POST /classification/label", catch_response=True
        ) as response:
            if response.status_code in (200, 409):
                response.success()
            else:
                response.failure(f"unexpected {response.status_code}: {response.text[:120]}")

    @task(1)
    def submit_generation(self) -> None:
        """Topic generation — a heavy Celery job that fills the worker queue."""
        if not GENERATION_ENABLED or not getattr(self, "authenticated", False):
            return
        body = {"project_id": PROJECT_ID, "doc_ids": DOC_IDS}
        self.client.post("/topics/generate", json=body, name="POST /topics/generate")

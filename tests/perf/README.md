# Performance & load testing (§7.7.4)

Two complementary measurements:

| What | How | Where it lives |
|---|---|---|
| **Timing** | Server-side instrumentation logs duration per request/job | `app/infrastructure/timing.py`, parsed by `scripts/utils/parse_timings.py` |
| **Load testing** | Locust generates concurrent traffic; correlate with timing logs + resource use | `tests/perf/locustfile.py` |

The Locust harness targets the **FastAPI gateway directly** so the measurement isolates
contention between the API, the Celery worker and MongoDB — not the Nginx/Next.js proxy.

---

## 1. Prerequisites

```bash
pip install -r requirements-dev.txt   # includes locust
```

A user account must exist (admins create users — there is no self-registration). The
harness logs in once per simulated user and reuses the JWT.

### Reaching FastAPI directly

In production FastAPI publishes **no host port** (only Nginx does). For load testing,
expose it on the test machine — add a port mapping for the `api` service, e.g. a
`docker-compose.perf.yml` override:

```yaml
services:
  api:
    ports:
      - "8000:8000"
```

Then `--host http://localhost:8000`. Alternatively run Locust as a one-off container on
the same docker network and use `--host http://api:8000`.

---

## 2. Configuration (environment variables)

| Variable | Required | Purpose |
|---|---|---|
| `LOCUST_USERNAME` / `LOCUST_PASSWORD` | yes | Credentials for the JWT login |
| `LOCUST_PROJECT_ID` | for pipeline | Project scope for `PipelineUser` |
| `LOCUST_CLASSIFIER_ID` | for Phase 2 | Classifier used by Phase 2 labelling |
| `LOCUST_DOC_IDS` | for generation | Comma-separated doc_ids (≥ 10) for topic generation |

`PipelineUser` only spawns when at least one of its operations is configured; the
read-only `SearchVisualisationUser` always works.

---

## 3. Running

### Read group only (no fixtures needed)

```bash
export LOCUST_USERNAME=loadtest LOCUST_PASSWORD=secret
locust -f tests/perf/locustfile.py --host http://localhost:8000 SearchVisualisationUser
```

Open http://localhost:8089 for the live UI, or run headless:

```bash
locust -f tests/perf/locustfile.py --host http://localhost:8000 SearchVisualisationUser \
    --headless -u 25 -r 5 -t 5m --csv tests/perf/results/read_25u
```

`-u` = peak users, `-r` = spawn rate/s, `-t` = duration. `--csv` writes
`*_stats.csv` / `*_failures.csv` (p50/p95/p99, RPS, failure counts).

### Both groups (read + pipeline, exercises the mutex)

```bash
export LOCUST_USERNAME=loadtest LOCUST_PASSWORD=secret
export LOCUST_PROJECT_ID=<uuid> LOCUST_CLASSIFIER_ID=<uuid>
locust -f tests/perf/locustfile.py --host http://localhost:8000 \
    --headless -u 30 -r 5 -t 5m --csv tests/perf/results/mixed_30u
```

Concurrent Phase 2 submissions on the same project return `409 LabellingLocked`; the
harness counts these as **successes** (graceful degradation), so a healthy run shows
low latency and zero 5xx even while many 409s are returned.

---

## 4. The ramp matrix (suggested)

Run each step for a few minutes; record p50/p95/failure-rate per step.

| Group | Concurrency steps |
|---|---|
| Read (`SearchVisualisationUser`) | 1 → 5 → 10 → 25 → 50 |
| Pipeline submissions | 1 → 2 → 4 |

Plot response time and failure rate against concurrency — that curve is the
"graceful degradation" evidence for the thesis.

---

## 5. Correlate with the server side

Locust reports **client-side** latency. During each run also capture:

* **Server-side timing** — `python scripts/utils/parse_timings.py "timings*.log"` after the
  run. Compare per-operation p95 against Locust's; rising **queue wait** vs flat
  **execution time** shows the bottleneck is contention, not the work itself.
* **Resources** — `docker stats` (or cAdvisor) for per-container CPU/RAM during the run.
* **Celery queue depth** — `redis-cli LLEN celery` sampled over time shows the queue
  backing up under pipeline load.

Results CSVs go in `tests/perf/results/` (gitignored).

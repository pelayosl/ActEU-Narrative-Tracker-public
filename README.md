# ActEU Narrative Tracker

**A full-stack research platform for discovering, classifying and visualising political narratives across a multilingual, multi-platform dataset.**

Final Degree Project (TFG), School of Computer Engineering, University of Oviedo. Developed within the EU-funded **ActEU** research consortium, which studies trust, legitimacy and polarisation in European democracies: https://acteu.org/.

🏆 Grade: 10, nominated for *Matrícula de Honor*

Should you want to read a copy of the project's official document, please contact me through my email or LinkedIn account.

---

## The problem

Political narratives don't stay inside fixed categories. A dataset of Twitter, Telegram and news documents tagged with only three broad themes (*immigration*, *climate change*, *gender issues*) hides the finer-grained subtopics (a specific policy debate, a controversy, a recurring frame) that actually matter for social science research.

The ActEU Narrative Tracker lets researchers **dynamically discover subtopics for any document subset they query**, validate and refine them with an LLM, train a reusable classifier from the result, and explore the outcome through an interactive dashboard, all without ever mutating the shared source dataset.

## Key features

- **Faceted document search** across a 9-language corpus (Twitter, Telegram, digital media), pre-annotated with NER and sentiment (currently only 3 languages are covered, but this is easily extensible).
- **Dynamic topic modelling pipeline**: BERTopic clustering → LLM-assisted cluster labelling → manual edit/merge → LLM topic reconciliation → FastText classifier training → dataset labelling, all resumable across sessions.
- **Project-scoped, non-destructive labelling**: results are stored as document *proxies* inside each user's project; the core corpus is never written to.
- **Interactive dashboard**: topic evolution over time, breakdowns by language and platform, top entities per topic ranked by weighted **PageRank** over an entity co-occurrence graph, and the most representative documents per topic.
- **Graceful LLM degradation**: if the university LLM endpoint is down, topic generation falls back to raw c-TF-IDF keyword labels and the pipeline keeps running rather than failing outright.
- **Async job infrastructure**: long-running NLP jobs (topic generation, reconciliation, training, labelling) run on Celery workers and stream live progress to the frontend over Server-Sent Events.
- **Role-based access**: admin-managed accounts, no public self-registration — researcher access only.

## Architecture

```
Browser
   │  HTTPS
   ▼
Nginx (TLS termination, reverse proxy) -- only service publishing ports 80/443
   │
   ▼
Next.js (BFF)  -- React, Zustand, TanStack Query, Recharts
   │  internal Docker network (incl. SSE streams)
   ▼
FastAPI  --  API Gateway → Services → Repositories (strict downward dependencies)
   │                     │
   ▼                     ▼
MongoDB (Motor)      Celery worker ──▶ Redis (broker + mutex lock store)
                          │
                          ▼
                 BERTopic · FastText · sentence-transformers
                 (google/embeddinggemma-300m) · Ollama LLM · igraph PageRank
```

The backend follows a strict layered architecture (API Gateway → Services → Repositories, with Infrastructure and Tasks as side dependencies) to keep business logic testable and free of framework or persistence concerns.

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, Tailwind CSS + shadcn/ui, Zustand, TanStack Query, Recharts, D3.js, NextAuth.js |
| Backend | FastAPI, sse-starlette, Motor (async MongoDB driver), Celery, Redis |
| Database | MongoDB |
| NLP pipeline | BERTopic, FastText, sentence-transformers (`google/embeddinggemma-300m`), UMAP, HDBSCAN, c-TF-IDF, custom LLM labelling, SHA-256 embedding cache (SQLite) |
| Graph analytics | `python-igraph` — weighted PageRank over an entity co-occurrence graph |
| Infrastructure | Docker, Docker Compose, Nginx, Let's Encrypt/Certbot, GitHub Actions, Dependabot |

## Quick start (local development)

The full installation, execution and user manuals are in **Chapter 11** of the thesis. Summary:

```bash
# Prerequisites: Docker Engine ≥24, Docker Compose v2 ≥2.20, Node.js 20 LTS, Git, OpenSSL

git clone <repo-url> && cd acteu-narrative-tracker

# Configure secrets (JWT, admin credentials, university LLM endpoint, HF_TOKEN)
cp .env.example .env   # fill in the required values

# Build and start the backend stack (MongoDB, Redis, FastAPI, Celery worker)
docker compose up -d --build
docker compose exec api python scripts/data/load_mongodb.py   # first run only

# Start the frontend dev server
cd frontend
cp .env.local.example .env.local
npm install && npm run dev
```

Open `http://localhost:3000` and log in with the admin credentials from your `.env`.

Production deployment (Docker Compose with Nginx, TLS via an internal CA, and MongoDB authentication enabled) is documented in section 11.1.3 of the thesis.

## Testing and evaluation

- **Unit and service tests** with repositories mocked (`AsyncMock`); **repository tests** run against a real, disposable MongoDB instance; **integration tests** drive the FastAPI app in-process via `httpx.AsyncClient`, exercising routing, auth middleware and domain-exception → HTTP translation.
- CI (GitHub Actions) runs the fast test suite (no NLP, no live infrastructure) on every push; NLP-heavy tests are tagged `slow` and run locally only.
- **Load testing** with Locust against the single-machine deployment confirmed zero request failures across all tested concurrency levels, correct serialisation of concurrent labelling jobs via a per-project Redis mutex, and identified database contention (not application logic) as the bottleneck under sustained read load — full timing and load-test tables in Chapter 10.


## Acknowledgements

Developed as a Final Degree Project by **Pelayo Sierra Lobo**, supervised by **Daniel Gayo Avello** and **Cristian González García**, School of Computer Engineering, University of Oviedo, within the EU-funded ActEU research consortium.

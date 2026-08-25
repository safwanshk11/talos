# TALOS — Autonomous Repository Maintenance System

[![Phase 3 Complete](https://img.shields.io/badge/Phase%203-Planning%20%26%20Patch%20Generation-blue.svg)](#)
[![Stack](https://img.shields.io/badge/Tech%20Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Docker-brightgreen.svg)](#)

TALOS is an autonomous repository maintenance system. It continuously monitors software repositories, detects routine maintenance problems, understands what needs to change, creates isolated fixes, verifies those fixes through real engineering checks, and delivers review-ready pull requests.

---

## Workflow Overview

```text
WATCH  ──►  DETECT  ──►  UNDERSTAND  ──►  PLAN  ──►  PATCH  ──►  VERIFY  ──►  DELIVER
                                                                                │
                                                                                ▼
                                                                       HUMAN REVIEW & MERGE
```

---

## Current Status: Phase 3 Complete

Phase 3 introduces TALOS's first AI reasoning capability — **Planning & Patch Generation** — for the vulnerable-dependency-upgrade workflow:

1. **Pluggable AI Provider**: A provider-agnostic `AIProvider` interface (`analyze_problem` / `generate_plan` / `generate_patch`) with two implementations — **Ollama** (local dev, e.g. `qwen2.5:7b`) and **Gemini** (deployment). Structured output is JSON-schema validated against Pydantic models, with a bounded retry budget before failing cleanly.
2. **Targeted Context Engine**: Builds a size-bounded "Maintenance Context Package" from Phase 2's own findings (the issue, manifest excerpt, affected files, lockfile presence, related tests, readiness signals) instead of sending the model the whole repository — every section records *why* it was included.
3. **Structured, Risk-Classified Planning**: The model produces a machine-validated plan (summary, root cause, target version, files to modify, actions, verification recommendations, risk). Risk is classified `LOW` / `MEDIUM` / `HIGH` — **HIGH risk always escalates instead of patching**.
4. **Isolated Workspace & TALOS Branch**: Each attempt clones into a disposable workspace and creates a `talos/fix-<issue>-<slug>` branch. The repository's primary branch is never touched, and nothing is ever pushed.
5. **Deterministic Dependency Updates**: The AI decides *what* needs to change; an actual package manager (`npm install pkg@version --package-lock-only`, or a PyPI-resolved pin for `requirements.txt`) performs the edit — TALOS never asks a model to hand-invent a lockfile.
6. **Patch Safety Enforcement**: Every model-proposed file edit is validated against path traversal, protected paths (`.git`, `node_modules`, etc.), file-size limits, and a modification-count cap before it touches disk.
7. **Real Git Diffs & Patch History**: A genuine `git diff` is generated and persisted per `PatchAttempt` — provider/model used, plan, analysis, files changed, status, and failure reason are all recorded. Prior attempts are never overwritten.
8. **Extended Lifecycle**: `OPEN → ANALYZING → PLANNING → PLANNED → SANDBOXING → PATCHING → PATCH_READY`, with `FAILED` / `ESCALATED` exits. Nothing is ever marked `VERIFIED` yet — that's Phase 4. The UI is explicit: *"Patch prepared. Awaiting verification."*

Phase 2 (**Repository Intelligence & Detection**, still fully active) provides the findings Phase 3 acts on:
- Isolated repository cloning & dependency parsing (`package.json`, `requirements.txt`, lockfiles)
- Deterministic vulnerability detection via the OSV API (`https://api.osv.dev`)
- SHA-256 issue deduplication & lifecycle (`last_seen_at`, auto-`RESOLVED`)
- Source-code import usage finder (`.ts`, `.js`, `.tsx`, `.jsx`, `.py`)
- Automation readiness assessment (`HIGH` / `MEDIUM` / `LOW`)
- Action Ledger & live operations dashboard (`WATCH`, `DETECT`, `UNDERSTAND`, `PLAN`, `PATCH`, `VERIFY`, `DELIVER`, `ESCALATE`)

---

## Tech Stack

* **Frontend**: React 18, TypeScript, Vite, Lucide Icons, Custom Developer Dark Theme
* **Backend**: FastAPI, Python 3.11, Async SQLAlchemy 2.0, Pydantic v2, HTTPX
* **AI Providers**: Ollama (local dev) or Gemini (deployment) behind a pluggable `AIProvider` interface
* **Database**: PostgreSQL 16
* **Infrastructure**: Docker & Docker Compose (Node.js/npm included in the backend image for deterministic dependency upgrades)

---

## Project Structure

```text
talos/
├── frontend/             # Vite + React + TypeScript Dashboard
│   ├── src/
│   │   ├── components/   # Sidebar, Header, MetricsOverview, RepositoryCard, ConnectGithubModal,
│   │   │                 # IssueDetailModal (Prepare Fix pipeline), DiffViewer
│   │   ├── pages/        # DashboardPage, RepositoryDetailPage, ActivityPage, SettingsPage
│   │   ├── services/     # Typed API Client
│   │   ├── types/        # TypeScript Interfaces
│   │   └── index.css     # Developer Infrastructure Theme
│   └── Dockerfile
├── backend/              # FastAPI Python Service
│   ├── app/
│   │   ├── api/v1/       # REST Routes (Auth, Repositories, Health)
│   │   ├── core/         # Security, Configuration, JWT
│   │   ├── db/           # Async SQLAlchemy Engine & Base
│   │   ├── models/       # Relational Database Models
│   │   ├── schemas/      # Pydantic Input/Output Validation
│   │   └── services/     # Business logic
│   │       ├── ai/                       # AIProvider interface + Ollama/Gemini implementations
│   │       ├── context_service.py        # Maintenance Context Package builder
│   │       ├── patch_service.py          # Phase 3 pipeline orchestrator
│   │       ├── git_workspace_service.py  # Isolated clone / branch / commit / diff
│   │       ├── dependency_updater_service.py  # Deterministic npm/pip upgrades
│   │       ├── patch_safety.py           # Path traversal / size / count enforcement
│   │       ├── scanner_service.py        # Phase 2 scan pipeline
│   │       └── github_service.py         # GitHub REST API client
│   └── Dockerfile
├── worker/               # Background Worker Architecture (reserved for Phase 4+)
├── docker-compose.yml    # Orchestration for PostgreSQL, Backend, Frontend
├── .env.example          # Environment Variables Template
└── README.md
```

---

## Quickstart & How to Run

### Option A: Using Docker Compose (Recommended)

1. Clone or navigate to the repository directory:
   ```bash
   cd /path/to/talos
   ```

2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Launch all containers:
   ```bash
   docker compose up --build
   ```

4. Access the applications:
   - **TALOS Operations Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Running Locally Outside Docker

#### 1. Start PostgreSQL
Ensure PostgreSQL is running locally on port 5432 with database `talos_db` and credentials `talos` / `talos_secret_pass`.

#### 2. Start Backend Service
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 3. Start Frontend App
```bash
cd frontend
npm install
npm run dev
```

---

## Required Environment Variables

Key environment variables in `.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PROJECT_NAME` | Application Name | `TALOS` |
| `SECRET_KEY` | JWT signing secret | `talos-super-secret-key-...` |
| `POSTGRES_SERVER` | Postgres DB hostname | `postgres` (or `localhost`) |
| `POSTGRES_PORT` | Postgres DB port | `5432` |
| `POSTGRES_USER` | Postgres DB username | `talos` |
| `POSTGRES_PASSWORD` | Postgres DB password | `talos_secret_pass` |
| `POSTGRES_DB` | Postgres DB name | `talos_db` |
| `GITHUB_CLIENT_ID` | Optional GitHub OAuth Client ID | `""` |
| `GITHUB_CLIENT_SECRET` | Optional GitHub OAuth Secret | `""` |
| `AI_PROVIDER` | `ollama` (local dev) or `gemini` (deployment) | `ollama` |
| `AI_MODEL` | Model name for the selected provider | `qwen2.5:7b` |
| `OLLAMA_BASE_URL` | Ollama server URL (use `http://host.docker.internal:11434` from Docker) | `http://localhost:11434` |
| `GEMINI_API_KEY` | Gemini API key, required when `AI_PROVIDER=gemini` | `""` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.0-flash` |

---

## Verification & Testing

To test the complete flow:
1. Open the dashboard at `http://localhost:3000`.
2. Click **Connect Repository** (or navigate to Settings).
3. Enter a GitHub Personal Access Token (PAT) with `repo` permissions.
4. Select a repository from the retrieved GitHub list and click **Connect**.
5. Observe the repository card appear on the dashboard with real language, default branch, and latest commit info.
6. Click **View** to inspect real GitHub metadata on the Repository Detail Page.
7. Click **Scan Repository** to run the Phase 2 pipeline — dependencies, OSV vulnerability findings, and readiness score populate for real.
8. Open a detected issue and click **Prepare Fix** to run the Phase 3 pipeline — TALOS gathers context, analyzes the issue, generates a risk-classified plan, creates an isolated branch, applies a deterministic dependency upgrade, and shows the real generated diff. The repository's primary branch is never touched.

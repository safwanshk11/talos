# TALOS — Autonomous Repository Maintenance System

[![Phase 4 Complete](https://img.shields.io/badge/Phase%204-Verification%20Engine-blue.svg)](#)
[![Stack](https://img.shields.io/badge/Tech%20Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Docker-brightgreen.svg)](#)

TALOS is an autonomous repository maintenance system. It continuously monitors software repositories, detects routine maintenance problems, understands what needs to change, creates isolated fixes, verifies those fixes through real engineering checks, and delivers review-ready pull requests.

See **[PHASES.md](PHASES.md)** for the full phase-by-phase build history — what each phase delivered, key files, how it was verified, and known limitations.

---

## Workflow Overview

```text
WATCH  ──►  DETECT  ──►  UNDERSTAND  ──►  PLAN  ──►  PATCH  ──►  VERIFY  ──►  DELIVER
                                                                                │
                                                                                ▼
                                                                       HUMAN REVIEW & MERGE
```

---

## Current Status: Phase 4 Complete

Phase 4 is TALOS's core differentiator: **AI-generated code is untrusted until verified with real engineering checks.** A `PATCH_READY` patch from Phase 3 is never assumed to work — it's proven, or rejected, by deterministic evidence.

1. **Real Docker Sandbox Isolation**: Verification runs in disposable `--rm` containers launched via docker-outside-of-docker (the backend talks to the *host's* Docker engine through a mounted socket). No TALOS secret (`GITHUB_PERSONAL_ACCESS_TOKEN`, `GEMINI_API_KEY`, `DATABASE_URL`, `SECRET_KEY`) is ever forwarded into the sandbox — `docker run` is never passed `-e`/`--env-file`. The sandbox runs on Docker's default bridge network, isolated from the compose network TALOS's own services use, with memory/CPU/pids/timeout limits.
2. **Repository-Specific Verification Plan**: `VerificationPlanBuilder` reads the patched workspace's actual `package.json` scripts — never invents a command that doesn't exist. Pipeline: `INSTALL → BUILD → TYPECHECK → LINT → TEST → SECURITY_AUDIT → VULNERABILITY_RESCAN`, with fail-fast on any required check that doesn't apply.
3. **The Original Vulnerability Is Re-Checked, Not Assumed Fixed**: after the sandbox checks run, TALOS reads the resolved dependency version out of the patched lockfile and re-queries the OSV API for the *original* advisory ID. A patch is only `VERIFIED` if that advisory is confirmed gone — passing build/tests alone is not enough.
4. **Evidence Over Confidence**: every check is stored and shown as real `PASSED` / `FAILED` / `SKIPPED` / `TIMED_OUT` with exit code, duration, and output excerpts — never an AI confidence score, and never a fabricated count (`84/84 tests`) unless a framework genuinely reported one. A failed *optional* check (e.g. an unrelated transitive-dependency security audit) is shown as failed, not hidden, even when it doesn't block the overall verdict.
5. **Full Verification History**: `VerificationRun` / `VerificationCheck` records are preserved per attempt, never overwritten — `VERIFIED` and `VERIFICATION_FAILED` are both permanent, inspectable evidence trails.

Earlier phases remain fully active and are what Phase 4 builds on — see **[PHASES.md](PHASES.md)** for the complete build history, architecture notes, and known limitations of every phase:
- **Phase 1** — GitHub integration, repository connection & dashboard
- **Phase 2** — repository scanning, OSV vulnerability detection, automation readiness
- **Phase 3** — AI-driven planning & patch generation (Ollama / Gemini), isolated branches, real diffs

---

## Tech Stack

* **Frontend**: React 18, TypeScript, Vite, Lucide Icons, Custom Developer Dark Theme
* **Backend**: FastAPI, Python 3.11, Async SQLAlchemy 2.0, Pydantic v2, HTTPX
* **AI Providers**: Ollama (local dev) or Gemini (deployment) behind a pluggable `AIProvider` interface
* **Database**: PostgreSQL 16
* **Infrastructure**: Docker & Docker Compose (Node.js/npm included in the backend image for deterministic dependency upgrades)
* **Verification Sandbox**: docker-outside-of-Docker — the backend launches isolated, ephemeral containers on the host's own Docker engine to run Phase 4 checks; it never executes untrusted repository code in-process

---

## Project Structure

```text
talos/
├── frontend/             # Vite + React + TypeScript Dashboard
│   ├── src/
│   │   ├── components/   # Sidebar, Header, MetricsOverview, RepositoryCard, ConnectGithubModal,
│   │   │                 # IssueDetailModal (fix pipeline), DiffViewer, VerificationReport,
│   │   │                 # RemoveRepositoryModal
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
│   │       ├── verification/             # Phase 4: sandbox execution, plan builder, orchestrator
│   │       ├── scanner_service.py        # Phase 2 scan pipeline
│   │       └── github_service.py         # GitHub REST API client
│   └── Dockerfile
├── worker/               # Background Worker Architecture (reserved for Phase 5+)
├── docker-compose.yml    # Orchestration for PostgreSQL, Backend, Frontend
├── .env.example          # Environment Variables Template
├── PHASES.md             # Full phase-by-phase build history
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

> **Phase 4 requirement**: the backend mounts `/var/run/docker.sock` to launch isolated
> verification sandboxes on your host's own Docker engine (docker-outside-of-Docker) —
> Docker Desktop (or an equivalent daemon) must be running before `docker compose up`.
> No extra setup is needed beyond that; `docker-compose.yml` already wires the socket
> and the shared `talos_workspaces` volume.

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
9. Once the patch is `PATCH_READY`, click **Run Verification** to run the Phase 4 pipeline — TALOS installs dependencies, builds, lints, tests, runs a security audit, and re-queries OSV to confirm the original advisory is actually gone, all inside an isolated sandbox container with no TALOS secrets. The report shows every check's real PASS/FAIL/SKIPPED — the patch is marked `VERIFIED` only if it earns it.

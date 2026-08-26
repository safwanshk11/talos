# TALOS — Autonomous Repository Maintenance System

[![Phase 6 Complete](https://img.shields.io/badge/Phase%206-Autonomous%20Operations%20Dashboard-blue.svg)](#)
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

## Current Status: Phase 6 Complete

Phase 6 turns TALOS into a coherent **autonomous operations control center**: a real visual identity (near-black design system, landing/login pages, animated app shell) plus a cross-repository dashboard built entirely from data the backend already produces — no fabricated metrics, no fake progress.

1. **Command Center**: STATUS / ATTENTION / **Active Operations** / Recent Outcomes / **Repository Health**, aggregated client-side across existing per-repo endpoints — no new backend rollup endpoints.
2. **Live Job-State Updates**: polling (`usePolling`, 8s, only while something is active) — the honest choice given no SSE/WebSocket infra exists. No simulated progress bars.
3. **Job Detail, Tabbed**: Overview / Analysis / Patch / Verification / Delivery / Activity — a tab appears only once its backing data actually exists, all sourced from real stored evidence (the same [Verification Evidence Integrity Rule](PHASES.md#verification-evidence-integrity-rule) from Phase 4).
4. **Maintenance Bay & Review Queue**: Maintenance Bay is the working-issues surface with real filters; Review Queue is the human PR handoff surface — real `PullRequest` rows, on-demand GitHub status sync, never auto-merged.
5. **Activity Log**: real cross-repository `ActionLog` records (replacing previously hardcoded placeholder entries), with filters and search.
6. **New Visual System**: near-black theme, a real marketing landing page, a login page built on TALOS's existing GitHub OAuth/PAT flow (no fake auth), an animated app shell with sidebar navigation, and a shared Framer Motion animation system (route transitions, scroll reveals, sliding active-tab indicators).

Earlier phases remain fully active and are what Phase 6 builds on — see **[PHASES.md](PHASES.md)** for the complete build history, architecture notes, and known limitations of every phase:
- **Phase 1** — GitHub integration, repository connection & dashboard
- **Phase 2** — repository scanning, OSV vulnerability detection, automation readiness
- **Phase 3** — AI-driven planning & patch generation (Ollama / Gemini), isolated branches, real diffs
- **Phase 4** — sandboxed verification engine, original-vulnerability re-scan, evidence-over-confidence reporting
- **Phase 5** — real GitHub pushes & pull requests, hard server-side delivery gate, never auto-merged

---

## Tech Stack

* **Frontend**: React 18, TypeScript, Vite, React Router v6, Framer Motion, Lucide Icons, near-black custom Tailwind design system
* **Backend**: FastAPI, Python 3.11, Async SQLAlchemy 2.0, Pydantic v2, HTTPX
* **AI Providers**: Ollama (local dev) or Gemini (deployment) behind a pluggable `AIProvider` interface
* **Database**: PostgreSQL 16
* **Infrastructure**: Docker & Docker Compose (Node.js/npm included in the backend image for deterministic dependency upgrades)
* **Verification Sandbox**: docker-outside-of-Docker — the backend launches isolated, ephemeral containers on the host's own Docker engine to run Phase 4 checks; it never executes untrusted repository code in-process
* **Delivery**: real GitHub pushes + pull requests via the GitHub REST API — no automatic merge, ever

---

## Project Structure

```text
talos/
├── frontend/             # Vite + React + TypeScript Operations Dashboard
│   ├── src/
│   │   ├── components/   # Sidebar, Header, MetricsOverview, RepositoryCard, ConnectGithubModal,
│   │   │                 # IssueDetailModal (tabbed fix pipeline), DiffViewer, VerificationReport,
│   │   │                 # RemoveRepositoryModal, PullRequestCard
│   │   │   └── ui/       # PageHeader, SectionCard, StatusBadge, EmptyState, Modal, Tabs,
│   │   │                 # PageTransition, AnimatedNumber, Reveal — shared design-system primitives
│   │   ├── layouts/      # AppShell (sidebar nav + route outlet, useAppShell() context)
│   │   ├── pages/        # LandingPage, LoginPage, CommandCenterPage, RepositoryRegistryPage,
│   │   │                 # RepositoryDetailPage, MaintenanceBayPage, ReviewQueuePage,
│   │   │                 # ActivityPage, SettingsPage
│   │   ├── hooks/        # useCrossRepoData, useDashboardStats, usePolling
│   │   ├── lib/          # statusGroups (active/attention/closed status classification)
│   │   ├── services/     # Typed API Client
│   │   ├── types/        # TypeScript Interfaces
│   │   └── index.css     # Near-black design tokens
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
│   │       ├── delivery_service.py       # Phase 5: commit reuse, artifact integrity, push, PR creation
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
10. Once the patch is `VERIFIED`, click **Create Pull Request** to run the Phase 5 pipeline — TALOS confirms the workspace still matches exactly what was verified, pushes the TALOS branch to GitHub, and opens a real pull request with an evidence-based description. The pipeline tracker shows `DELIVERING` complete and a **View on GitHub** link to the real, open PR. TALOS never merges it — that's on you.

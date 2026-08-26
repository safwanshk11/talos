# TALOS — Autonomous Repository Maintenance System

[![Phase 6.5 Complete](https://img.shields.io/badge/Phase%206.5-Decision%20Engine%20%26%20Autonomy%20Governance-blue.svg)](#)
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

## Current Status: Phase 6.5 Complete

Phase 6.5 answers the question earlier phases left open — **who decides whether TALOS should act in the first place?** TALOS is now a policy-governed autonomous operator, not just a pipeline that runs whenever a human clicks a button.

1. **Deterministic Decision Engine**: every maintenance issue is evaluated — repository state, risk, protected paths, verification capability, conflicts — against a fixed precedence order before TALOS touches anything. No AI call ever decides whether autonomous action is safe; the model only supplies structured input the engine evaluates.
2. **Five real outcomes**: `AUTO_EXECUTE` (patch → verify → deliver, chained, still human-reviewed), `PREPARE_ONLY` (patch and stop), `APPROVAL_REQUIRED` (persists the exact plan already produced and waits for a real **Approve & Continue** / **Reject**), `ESCALATE`, `IGNORE` — plus `BLOCKED_BY_CONFLICT` for repository-level collision.
3. **Per-repository Autonomy Policy**: Conservative / Balanced *(default)* / Autonomous presets, four editable tiers (security patches, patch/minor/major dependency updates), and a protected-paths editor (`**/auth/**`, `**/payments/**`, etc.) — major updates and protected paths can never be set to auto-execute, enforced server-side.
4. **Backend-enforced, not a UI suggestion**: approval/rejection endpoints re-validate job state server-side; a duplicate `prepare-fix` call on an issue already awaiting approval is deterministically re-blocked by the same conflict check, not silently allowed through.
5. **Explainable, not confident**: every decision shows the real rules that matched and what blocked it — never a fabricated confidence score — visible in a new Job Detail **Decision** tab and the real Action Ledger.

Earlier phases remain fully active and are what Phase 6.5 builds on — see **[PHASES.md](PHASES.md)** for the complete build history, architecture notes, and known limitations of every phase:
- **Phase 1** — GitHub integration, repository connection & dashboard
- **Phase 2** — repository scanning, OSV vulnerability detection, automation readiness
- **Phase 3** — AI-driven planning & patch generation (Ollama / Gemini), isolated branches, real diffs
- **Phase 4** — sandboxed verification engine, original-vulnerability re-scan, evidence-over-confidence reporting
- **Phase 5** — real GitHub pushes & pull requests, hard server-side delivery gate, never auto-merged
- **Phase 6** — near-black visual system, autonomous operations Command Center, tabbed Job Detail, Maintenance Bay & Review Queue

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
│   │       ├── decision_service.py       # Phase 6.5: deterministic Decision Engine + policy/conflict services
│   │       ├── scanner_service.py        # Phase 2 scan pipeline
│   │       └── github_service.py         # GitHub REST API client
│   ├── tests/             # pytest — includes Decision Engine unit tests
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
11. On the Repository Detail page, open **Autonomy Policy** to see the Phase 6.5 Decision Engine: switch modes (Conservative / Balanced / Autonomous), edit a tier's action, or add a protected path. Then click **Prepare Fix** on an issue — the Job Detail modal's new **Decision** tab shows exactly which policy and rules TALOS evaluated and why it landed on `AUTO_EXECUTE` / `APPROVAL_REQUIRED` / `ESCALATE`. If `APPROVAL_REQUIRED`, a real **Approve & Continue** / **Reject** pair is shown — approving resumes the exact plan already produced, never a new one.

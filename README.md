# TALOS — Autonomous Repository Maintenance System

[![Phase 8 Complete](https://img.shields.io/badge/Phase%208-Production%20Hardening-blue.svg)](#)
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

## Current Status: Phase 8 Complete

Phase 8 is not a feature phase — it's a hardening pass over Phases 1-7's product surface. Scope was deliberately frozen (no auto-merge, no new integrations); everything below fixes something a full-repository audit found actually broken or actually missing.

1. **Fail-fast configuration**: TALOS now validates its own configuration at startup — an unsafe `SECRET_KEY` default or a missing `GEMINI_API_KEY` under `AI_PROVIDER=gemini` is a hard boot failure in `ENVIRONMENT=production`, and a loud warning in development, instead of a confusing failure three requests later.
2. **No more orphaned workspaces**: every isolated git clone TALOS creates to prepare a patch is now reclaimed automatically once its job is genuinely done (`WorkspaceReaperService`) — previously they accumulated on disk forever.
3. **Real production frontend build**: the frontend container now runs a real `tsc && vite build`, served by `vite preview`, as a non-root user — not the Vite dev/HMR server the prior image ran as its long-running process.
4. **Both containers have real Docker healthchecks**, and `docker-compose.yml`'s frontend now waits on the backend's actual health rather than plain startup ordering.
5. **A stray secret-exposure gap closed**: the one dependency-resolution step that ran outside the Phase 4 sandbox now has TALOS's secrets explicitly stripped from its environment.
6. **A React error boundary**, a fixed silent-failure state on the Command Center dashboard, and reduced-motion support on every route transition and landing-page reveal.

See **[PHASES.md](PHASES.md#phase-8--production-hardening--deployment--complete)** for the full audit findings, what was fixed, what was confirmed already sound, and — just as importantly — the explicit list of what was deliberately left out of scope.

Earlier phases remain fully active and are what Phase 8 hardens — see **[PHASES.md](PHASES.md)** for the complete build history, architecture notes, and known limitations of every phase:
- **Phase 1** — GitHub integration, repository connection & dashboard
- **Phase 2** — repository scanning, OSV vulnerability detection, automation readiness
- **Phase 3** — AI-driven planning & patch generation (Ollama / Gemini), isolated branches, real diffs
- **Phase 4** — sandboxed verification engine, original-vulnerability re-scan, evidence-over-confidence reporting
- **Phase 5** — real GitHub pushes & pull requests, hard server-side delivery gate, never auto-merged
- **Phase 6** — near-black visual system, autonomous operations Command Center, tabbed Job Detail, Maintenance Bay & Review Queue
- **Phase 6.5** — deterministic Decision Engine, per-repository autonomy policy, approval workflow, protected paths
- **Phase 7** — GitHub webhook intake, scheduled monitoring, event-driven scanning, self-trigger loop prevention

---

## Safety Model

TALOS is built so that safety never depends only on the frontend or on a human remembering to check something:

- **TALOS never merges a pull request.** Every fix stops at an open PR for human review, in every phase, with no configuration flag that changes this.
- **Verification and delivery are hard-gated server-side.** A patch is marked `VERIFIED` only if every real check (install/build/test/security-audit/original-advisory re-query) actually passes inside an isolated, no-secrets sandbox — and delivery re-checks that the verified artifact's hash still matches what's about to be pushed before pushing it.
- **The Decision Engine (Phase 6.5) is the single authority on autonomy**, and it's enforced in the backend, not the UI: a direct API call attempting to skip an `APPROVAL_REQUIRED` gate is rejected the same way a UI click would be, because both paths call the same server-side check.
- **Protected paths, risk tiers, and per-repository policy** (Conservative/Balanced/Autonomous presets, or manual tier overrides) all live in the database and are evaluated fresh on every job — nothing is cached as "already decided."
- **Continuous monitoring (Phase 7) never increases what TALOS is allowed to do autonomously** — a webhook- or schedule-triggered job passes through the exact same Decision Engine a manual click would.
- **The verification sandbox never receives TALOS's own secrets** (GitHub token, AI provider key, database credentials, JWT signing key) — confirmed by direct audit of every `docker run` invocation in Phase 8.

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
│   │   │                 # RemoveRepositoryModal, PullRequestCard, ErrorBoundary
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
│   ├── Dockerfile         # Multi-step: tsc+vite build, non-root, HEALTHCHECK
│   └── .dockerignore
├── backend/              # FastAPI Python Service
│   ├── app/
│   │   ├── api/v1/       # REST Routes (Auth, Repositories, Health, Webhooks)
│   │   ├── core/         # Security, Configuration (+ startup config validation), JWT
│   │   ├── db/           # Async SQLAlchemy Engine & Base
│   │   ├── models/       # Relational Database Models
│   │   ├── schemas/      # Pydantic Input/Output Validation
│   │   └── services/     # Business logic
│   │       ├── ai/                       # AIProvider interface + Ollama/Gemini implementations
│   │       ├── context_service.py        # Maintenance Context Package builder
│   │       ├── patch_service.py          # Phase 3 pipeline orchestrator
│   │       ├── git_workspace_service.py  # Isolated clone / branch / commit / diff
│   │       ├── dependency_updater_service.py  # Deterministic npm/pip upgrades (secret-scrubbed env)
│   │       ├── patch_safety.py           # Path traversal / size / count enforcement
│   │       ├── verification/             # Phase 4: sandbox execution, plan builder, orchestrator
│   │       ├── delivery_service.py       # Phase 5: commit reuse, artifact integrity, push, PR creation
│   │       ├── decision_service.py       # Phase 6.5: deterministic Decision Engine + policy/conflict services
│   │       ├── monitoring_service.py     # Phase 7 event intake/scheduler + Phase 8 WorkspaceReaperService
│   │       ├── scanner_service.py        # Phase 2 scan pipeline
│   │       └── github_service.py         # GitHub REST API client
│   ├── tests/             # pytest — Decision Engine + continuous monitoring unit/integration tests
│   ├── Dockerfile         # HEALTHCHECK via /api/v1/health
│   └── .dockerignore
├── docker-compose.yml    # Orchestration for PostgreSQL, Backend, Frontend (healthchecked)
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
| `ENVIRONMENT` | `development` or `production` — controls whether unsafe config is a warning or a boot failure | `development` |
| `SECRET_KEY` | JWT signing secret — **must** be changed before `ENVIRONMENT=production`, TALOS refuses to boot otherwise | `talos-super-secret-key-...` |
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
| `GEMINI_API_KEY` | Gemini API key — **required** when `AI_PROVIDER=gemini`, TALOS refuses to boot in production without it | `""` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.0-flash` |
| `GITHUB_WEBHOOK_SECRET` | HMAC secret for verifying inbound GitHub webhooks (Phase 7) | `""` |
| `WORKSPACE_RETENTION_HOURS` | Hours a completed job's patch workspace is kept on disk before reclamation (Phase 8) | `24` |

See `.env.example` for the complete list, including the Phase 4 `VERIFICATION_*` sandbox settings (images, timeouts, resource limits).

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
12. On the Repository Detail page, open **Monitoring** to opt a repository into Phase 7 continuous scanning (Daily/Weekly) and toggle relevant-push scanning — off by default (`manual`) on every repository so a freshly-deployed scheduler never starts autonomously scanning real connected repositories without you asking. With `GITHUB_WEBHOOK_SECRET` set and a GitHub webhook pointed at `/api/v1/webhooks/github` (requires a public URL, e.g. via ngrok in local dev), a push touching `package.json`/a lockfile/`requirements.txt` on the default branch triggers a real scan automatically; a docs-only push or a push to one of TALOS's own `talos/fix-*` branches is correctly skipped. Command Center's header shows how many repositories are monitored and when the next scheduled check is due.
13. Check `curl http://localhost:8000/api/v1/health` — `200` with `"database": "healthy"` means the stack booted clean; `docker compose ps` should show both `backend` and `frontend` as `healthy`, not just `running`. Try `docker compose restart backend` — repositories, jobs, scans, and PRs all survive (nothing is held only in memory), and any scan/job genuinely interrupted by the restart is reconciled to a clear `failed` state on the next boot rather than staying stuck.

---

## Deployment

The implemented architecture is deliberately the simplest one that's actually correct for this product, not a copy of a generic microservice diagram:

```text
GitHub ──(OAuth + Webhooks)──► TALOS Frontend (static build, vite preview)
                                        │  /api proxy
                                        ▼
                                TALOS Backend (FastAPI, uvicorn)
                                   │            │
                                   ▼            ▼
                              PostgreSQL   asyncio background task
                                            (Phase 7 scheduler +
                                             Phase 8 workspace reaper)
                                   │
                                   ▼
                    docker-outside-of-docker ──► ephemeral, no-secret
                    (host socket mount)           verification sandbox
```

- **No Redis/Celery/job-queue infrastructure.** Continuous monitoring and workspace reclamation both run as `asyncio` background tasks inside the same FastAPI process (`app/main.py`'s `lifespan`), matching the pattern this project has used since Phase 6. This is a genuine, intentional deviation from a conventional "API + worker + queue" diagram — correct and sufficient for a single-instance deployment, and explicitly not something Phase 8 tried to force into a bigger shape it doesn't need. It does mean monitoring/reaping pause with the backend process and resume when it restarts (verified — see the Phase 8 restart test in `PHASES.md`), and it does not horizontally scale past one backend instance.
- **Frontend**: `docker build` produces a real production bundle (`tsc && vite build`) served by `vite preview` — not a full CDN/static-host pipeline, but genuinely minified, typechecked, production JS rather than a dev server.
- **Backend**: standard `uvicorn` ASGI process; stateless aside from its background tasks, so it can be redeployed/restarted safely (see the restart guarantees above).
- **Database**: PostgreSQL 16, any managed provider (RDS, Cloud SQL, etc.) works — TALOS only needs a connection string via `DATABASE_URL`. No backup automation is configured by TALOS itself; rely on the managed provider's backups in a real deployment.
- **GitHub webhook**: requires a publicly reachable HTTPS URL pointed at `/api/v1/webhooks/github` with `GITHUB_WEBHOOK_SECRET` set to the same secret configured in the GitHub repository's webhook settings — not needed for manual scans/fixes, only for Phase 7's automatic push-triggered scanning.
- **OAuth callback**: `GITHUB_REDIRECT_URI` must point at your real frontend origin in production, not `localhost` — startup validation warns if it doesn't.
- **AI provider**: use `AI_PROVIDER=ollama` only where an Ollama server is actually reachable (local dev); use `AI_PROVIDER=gemini` for any real deployment. TALOS never attempts to reach a developer's local Ollama server from a cloud deployment — the two are entirely separate `AIProvider` implementations behind one interface, and switching is one environment variable.

---

## Known Limitations

Honest, current, and specific — not aspirational:

- **Single-instance scheduler.** Continuous monitoring and workspace reclamation are in-process `asyncio` tasks, not a distributed job queue — correct for one backend instance, doesn't horizontally scale to multiple.
- **No formal database migration tooling.** Alembic is installed but unused; schema evolves via `ADD COLUMN IF NOT EXISTS` in the startup lifespan. Safe so far because affected tables have been empty at each change, but this is real technical debt, not a design choice.
- **GitHub PAT is stored in plaintext** in the database (`github_connections.access_token`), not encrypted at rest.
- **GitHub OAuth requests the broad `repo` scope** — classic GitHub OAuth Apps don't offer a narrower per-repository grant; a GitHub App with fine-grained permissions would, but is a larger change than this project has made.
- **Live job cancellation is unavailable** — once a scan/patch/verification is running, it runs to completion or failure; there is no "stop" button.
- **Autonomous repair retries are intentionally limited.** TALOS does not automatically re-attempt a failed patch — a failure surfaces honestly rather than silently retrying into a different outcome.
- **`npm audit`/OSV give deterministic security coverage; `pip`'s ecosystem coverage is comparatively thinner** — exact check availability depends on what a given repository's own tooling reports.
- **The verification sandbox has outbound internet access** (`--network bridge`, needed so `npm install`/`pip install` can actually resolve packages) — it is isolated from TALOS's own internal services, not from the public internet.
- **TALOS creates pull requests but never merges them, under any configuration.** This is a permanent design decision, not a current-version limitation.

---

## AI Disclosure

**AI used to build TALOS:** Claude (Anthropic), via Claude Code, was used throughout this project's development — architecture decisions, implementation, debugging, and the audits behind Phase 8's hardening pass.

**AI used by TALOS at runtime:** a pluggable `AIProvider` interface behind exactly two implementations — **Ollama** (local models, used in local development) or **Gemini** (Google's API, used in any real deployment). The AI model is used only to *analyze* a detected issue and *propose* a structured fix plan; it never executes code, never decides whether a fix is safe to apply autonomously (that's the deterministic, non-AI Decision Engine's job), and never hand-edits a lockfile — actual dependency version changes are applied by deterministic package-manager operations, not by the model writing file contents from scratch. No other AI model or service is used at runtime.

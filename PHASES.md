# TALOS — Phase Tracker

TALOS is built incrementally, one phase at a time, on the philosophy:

> Don't tell developers how to fix their repositories. Fix them — and prove the fix works.

This document is the running build history: what each phase actually delivered, the
key files involved, how it was verified, and known limitations at the time. Update it
at the end of every phase — it's the fastest way for anyone (including a future agent
picking up this project) to know what's real versus planned without re-deriving it
from the codebase.

Status legend: ✅ Complete · 🚧 In Progress · 🔜 Planned

---

## Phase 1 — Foundation & GitHub Integration ✅ Complete

**Goal:** Stand up the core stack and let a user connect a GitHub repository to TALOS.

**Delivered:**
- React + TypeScript (Vite) frontend, FastAPI + async SQLAlchemy backend, PostgreSQL, Docker Compose.
- GitHub integration via Personal Access Token or OAuth app flow.
- Repository listing (from GitHub) → connect → persisted `Repository` row → shown on the dashboard with real metadata (language, default branch, latest commit).
- Local-dev auth: a single auto-provisioned `talos_developer` user (not multi-tenant auth — see Limitations).
- Loading/error/empty states throughout.

**Key files:** `backend/app/api/v1/auth.py`, `backend/app/services/github_service.py`, `backend/app/services/repository_service.py`, `backend/app/models/{user,github,repository}.py`, `frontend/src/components/ConnectGithubModal.tsx`, `frontend/src/pages/DashboardPage.tsx`.

**Known limitations:**
- Auth is a single-user local-dev convenience (`api/deps.py` auto-creates/returns one user), not real multi-tenant authentication.
- GitHub PAT is stored in plaintext in `github_connections.access_token` — flagged, not yet fixed.
- No formal migration tooling (see Phase 2 note) — schema evolves via `Base.metadata.create_all` plus manual `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements in `main.py`'s startup lifespan.

---

## Phase 2 — Repository Intelligence & Detection ✅ Complete

**Goal:** Clone a connected repository, parse its dependencies, and detect real vulnerabilities.

**Delivered:**
- Isolated repository cloning into a temp workspace, `package.json` / `requirements.txt` / lockfile parsing.
- Deterministic vulnerability detection via the OSV API (`https://api.osv.dev`) — no AI in the detection path.
- SHA-256 issue fingerprinting for deduplication across scans; issues no longer detected are auto-marked `RESOLVED`.
- Source-code import usage finder (`.ts`/`.js`/`.tsx`/`.jsx`/`.py`) — flags which files actually reference a vulnerable package.
- Automation Readiness assessment (`HIGH`/`MEDIUM`/`LOW`) from manifest/lockfile/build/test/lint/typecheck/CI signals.
- Action Ledger (`WATCH → DETECT → UNDERSTAND → PLAN → PATCH → VERIFY → DELIVER → ESCALATE` step vocabulary) and a live scan-progress UI.

**Key files:** `backend/app/services/scanner_service.py`, `backend/app/services/readiness_service.py`, `backend/app/services/usage_finder_service.py`, `backend/app/models/{scan,dependency,readiness,future}.py`, `frontend/src/components/ScanProgressModal.tsx`, `frontend/src/pages/RepositoryDetailPage.tsx`.

**Bugs found and fixed (discovered while building Phase 3, root-caused to Phase 2 code):**
- `scanner_service.py` was missing `import re` — any OSV result with a raw CVSS-string severity (no `database_specific.severity`) crashed the whole scan. Never caught because the pipeline had never been run end-to-end against real seeded data before Phase 3.
- The live database's `action_logs` and `maintenance_issues` tables predated columns already present in their models (`repository_id`/`scan_id`/`fingerprint`/`package_name`/etc.) — every Phase 2 ledger write and issue upsert had been silently failing since before this session. Patched via `ADD COLUMN IF NOT EXISTS` in `main.py`.
- The scanner's fallback for "no fixed version reported by OSV" was the human-readable string `"Latest patch"`, which is not a valid install target for any package manager. Changed to the npm-valid dist-tag `"latest"`, with PyPI-JSON-API resolution added for the pip path (pip has no equivalent tag).

**Known limitations:**
- `npm`/`pip` are the only supported ecosystems.
- No formal migration tooling — see Phase 1.

---

## Phase 3 — Planning & Patch Generation ✅ Complete

**Goal:** Take one detected issue, reason about it with AI, and produce a real, minimal, isolated patch — without ever touching the primary branch or claiming success prematurely.

**Delivered:**
- **Pluggable `AIProvider` interface** (`analyze_problem` / `generate_plan` / `generate_patch`) with two implementations: **Ollama** (local dev, `qwen2.5:7b` by default) and **Gemini** (deployment). Structured output is JSON-schema-validated against Pydantic models with a bounded retry budget.
- **Context Engine**: builds a size-bounded "Maintenance Context Package" from Phase 2's own findings (issue data, manifest excerpt, affected files, lockfile presence, related tests, readiness signals) instead of sending the model the whole repo — every section records *why* it was included.
- **Structured, risk-classified planning**: `LOW`/`MEDIUM`/`HIGH` risk; **HIGH always escalates instead of patching**.
- **Isolated workspace + branch**: each attempt clones into a disposable workspace and creates `talos/fix-<issue>-<slug>`. The primary branch is never touched and nothing is ever pushed.
- **Deterministic dependency updates**: the AI decides *what* to change; an actual package manager (`npm install pkg@version --package-lock-only`, or a PyPI-resolved pin for `requirements.txt`) performs the edit — no AI-hand-invented lockfiles.
- **Patch safety enforcement**: path traversal / protected-path / file-size / modification-count checks on every model-proposed edit before it touches disk.
- **Real git diffs**, persisted per `PatchAttempt` with provider/model, plan, analysis, files changed, status, and failure reason. Prior attempts are never overwritten.
- Lifecycle: `OPEN → ANALYZING → PLANNING → PLANNED → SANDBOXING → PATCHING → PATCH_READY`, with `FAILED`/`ESCALATED` exits. UI is explicit: *"Patch prepared. Awaiting verification."* — never "fixed."

**Key files:** `backend/app/services/ai/` (`base.py`, `ollama_provider.py`, `gemini_provider.py`, `factory.py`, `schemas.py`, `prompts.py`), `backend/app/services/{context_service,patch_service,git_workspace_service,dependency_updater_service,patch_safety}.py`, `frontend/src/components/{IssueDetailModal,DiffViewer}.tsx`.

**Verified:** real end-to-end run against a seeded local fixture repo — live OSV query found the axios 0.21.1 vulnerability, Ollama produced a genuine structured plan (`risk: LOW`, `target_version: latest`), a real `npm install axios@latest --package-lock-only` bumped the dependency, a real `git diff` was generated, and the original repository was confirmed untouched (still one commit on `main`).

**Known limitations:**
- No automated patch-generation retry loop (Phase 3 spec made this explicitly optional).
- Synchronous request/response — no live incremental progress during `prepare-fix`, matching Phase 2's scan pattern rather than introducing new worker infrastructure.
- If a `MaintenanceIssue`'s package has no matching `Dependency` row (stale scan), the deterministic update is skipped and the job fails cleanly rather than faking a patch.

---

## Phase 4 — Verification Engine ✅ Complete

**Goal:** AI-generated code is untrusted until TALOS verifies it with real engineering checks — never claim a patch works without proof.

**Delivered:**
- **Real Docker sandbox isolation** via docker-outside-of-Docker: the backend launches disposable `--rm` containers on the *host's own* Docker engine (mounted socket), never executing untrusted repository code in-process.
  - No TALOS secret is ever forwarded — `docker run` is never passed `-e`/`--env-file`.
  - `--network bridge` (Docker's default), isolated from the compose network TALOS's own services communicate over.
  - Memory/CPU/pids limits plus a hard wall-clock timeout per check.
  - Patch workspaces shared via a fixed-name Docker volume (`talos_workspaces`) mounted into both the backend and every sandbox container it launches.
- **`VerificationPlanBuilder`**: reads the patched workspace's actual `package.json` scripts (not cached readiness booleans) and only plans commands that genuinely exist. Pipeline: `INSTALL → BUILD → TYPECHECK → LINT → TEST → SECURITY_AUDIT → VULNERABILITY_RESCAN`, fail-fast on any required check.
- **The original vulnerability is re-checked, not assumed fixed**: reads the resolved dependency version from the patched lockfile and re-queries OSV for the *original* advisory ID. `VERIFIED` requires that advisory to be confirmed gone — passing build/tests alone is not enough.
- **Evidence over confidence**: every check stores real exit code, duration, and output excerpts, shown as `PASSED`/`FAILED`/`SKIPPED`/`TIMED_OUT` — never an AI confidence score, never a fabricated test count. A failed *optional* check (e.g. an unrelated transitive-dependency security audit) is shown as failed, not hidden, even when it doesn't block the overall verdict.
- **`VerificationRun`/`VerificationCheck` models**: full history preserved, never overwritten.

**Key files:** `backend/app/services/verification/` (`sandbox_service.py`, `plan_builder.py`, `verification_service.py`), `backend/app/schemas/verification.py`, `frontend/src/components/VerificationReport.tsx`, `docker-compose.yml` (socket mount + `talos_workspaces` volume), `backend/Dockerfile` (docker-cli).

**Verified both directions against the demo repository:**
- **Positive**: `INSTALL`/`BUILD`/`LINT`/`TEST` genuinely passed in a real sandboxed `npm ci`; `SECURITY_AUDIT` genuinely failed (4 real high-severity transitive vulnerabilities) and was shown as failed without blocking the verdict since it's optional; `VULNERABILITY_RESCAN` confirmed axios 0.21.1 → 1.19.0 removed advisory `GHSA-3p68-rc4w-qgx5`. Result: `VERIFIED`.
- **Negative**: temporarily pushed a commit breaking the demo repo's `test` script (`exit 1`), ran the identical production pipeline with no special-casing — real `TEST` failure, fail-fast skip of `SECURITY_AUDIT`/`VULNERABILITY_RESCAN`, result: `VERIFICATION_FAILED`. Then reverted and re-verified clean.

**Bugs found and fixed while building this phase:**
- Docker Compose project-prefixes named volumes (`talos_workspaces` → `talos_talos_workspaces`), which silently pointed the sandbox at a freshly-created *empty* volume instead of the real one — fixed by pinning the volume's literal `name:` in `docker-compose.yml`.
- `npm audit --json` output was tail-truncated to the storage limit *before* being parsed, corrupting the JSON structure — fixed by parsing the full output first and truncating only what gets persisted.
- `verified_patches_count` on the dashboard had been hardcoded to `0` since Phase 1 — now a real count of jobs with `status='verified'`.

**Known limitations:**
- No live cancellation of an in-flight verification run (synchronous architecture, same as Phases 2–3; spec explicitly deprioritized this).
- No automated patch-regeneration retry loop on verification failure (spec made this explicitly optional and warned against instability; failed patches are preserved for human inspection instead).
- `SECURITY_AUDIT` is npm-only — the pip path has no deterministic audit tool wired in and is marked `SKIPPED` with a stated reason.
- Exact test counts (`84/84`) are never displayed unless a framework genuinely reports them in a parseable form — see [Verification Evidence Integrity Note](#verification-evidence-integrity-rule) below.

### Verification Evidence Integrity Rule

Standing rule for this project, in force from Phase 4 onward:

> **Only display verification evidence TALOS actually measured.**

- If TALOS only knows a check exited 0, display `PASS` — never a fabricated count like `84/84 PASS`.
- A skipped check is always shown with its real reason (e.g. `SECURITY_AUDIT: SKIPPED — deterministic audit integration unavailable for this ecosystem`), never hidden or reworded into something more flattering.
- This applies to the UI today and must apply to Phase 5 pull-request descriptions too: they are generated from the same stored `VerificationCheck` rows, not re-summarized with invented precision.

---

## Phase 5 — GitHub PR Delivery 🔜 Planned

Push the TALOS branch, open a pull request with an evidence-based description (real check results per the integrity rule above), track PR status. No automatic merge.

## Phase 6 — Autonomous Operations Dashboard 🔜 Planned

Cross-repository view of everything TALOS is doing/has done: active jobs, verification history, escalations awaiting human review.

## Phase 7 — Production Hardening + Hackathon Polish 🔜 Planned

Real multi-tenant auth, encrypted secret storage (GitHub PAT is currently plaintext — see Phase 1), formal DB migrations (currently ad-hoc `ALTER TABLE` statements — see Phase 1/2), broader ecosystem support, general robustness pass.

---

## Cross-Phase Technical Debt (tracked, not yet addressed)

- **No formal migration tooling.** Alembic is an installed dependency but unused; schema changes are applied via `ADD COLUMN IF NOT EXISTS` statements in `main.py`'s startup lifespan. Safe so far because every affected table has been empty at the time of change, but this will not scale past a certain point.
- **GitHub PAT stored in plaintext** (`github_connections.access_token`).
- **Single-user local-dev auth** — no real multi-tenancy yet.

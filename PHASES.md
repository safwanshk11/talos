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

## Phase 5 — GitHub Delivery & Pull Requests ✅ Complete

**Goal:** Take the exact patch that passed Phase 4 verification and deliver it as a real, review-ready GitHub pull request — never regenerated, never auto-merged.

**Delivered:**
- **Hard delivery gate enforced server-side**: a job must be `verified` (or resuming from `delivering`/`delivery_failed`) with a real ready `PatchAttempt` and a `VerificationRun` whose `status == "verified"` — checked in `DeliveryService.deliver()` itself, not just hidden behind a frontend button. A direct API call against a `patch_ready` or `verification_failed` job is rejected with `400 DELIVERY BLOCKED` every time.
- **Deliver the exact verified artifact, never a new one**: no `AIProvider` call anywhere in the delivery path. The commit that gets pushed is the *same* local commit Phase 3 already created and Phase 4 already verified (`PatchAttempt.commit_sha`) — Phase 5 never re-commits.
- **Artifact integrity check**: immediately before push, TALOS recomputes the workspace's live `git diff` against the stored `base_sha` and SHA-256s it, then compares that hash to a SHA-256 of the diff Phase 4 actually verified (`PatchAttempt.patch_diff`). A mismatch — e.g. the workspace's git history was altered after verification — blocks delivery with `Patch changed after verification. Re-verification required.` rather than silently continuing.
- **Branch safety**: verifies the workspace's current branch is exactly the expected `talos/fix-<issue>-<slug>` branch (never `main`/`master`/the repo's default branch) before pushing.
- **Real push + real PR**: pushes the TALOS branch via a credential-in-URL `git push` (never written to `.git/config`) and opens an actual GitHub PR (`head` = TALOS branch, `base` = repository default branch) via the GitHub REST API.
- **Evidence-based PR body**, generated from real stored data only: problem (from the `MaintenanceIssue`), changes (from the stored `MaintenancePlan.actions`), a verification table built directly from `VerificationCheck` rows (`PASSED`/`FAILED`/`SKIPPED` — SKIPPED always includes its real reason, never reworded as PASS), risk level, and files-changed count. No fabricated test counts — same [Verification Evidence Integrity Rule](#verification-evidence-integrity-rule) Phase 4 established.
- **Idempotency + partial-delivery recovery**: one `PullRequest` row per `MaintenanceJob`. A second delivery request for an already-delivered job returns the existing PR instead of creating a duplicate (checked *before* the status gate, since a successful delivery moves the job off `verified`). A delivery that fails partway (e.g. push succeeds, PR creation fails) leaves the job in `delivery_failed`; retrying resumes — it does not re-commit, and re-push is a safe force-push of TALOS's own already-pushed branch — and checks GitHub for an existing PR on that head branch before creating a new one.
- **State machine**: `verified → delivering → delivery_failed | delivered`, mirrored on both `MaintenanceJob.status` and `MaintenanceIssue.status` (`DELIVERED`), with a real `PullRequest.status` (`pending/committing/pushing/creating_pr/delivered/delivery_failed`) and a separate `PullRequest.github_status` (`open/merged/closed`, refreshable on demand) tracking GitHub's own state.
- **Action Ledger** entries at every real step (`DELIVER` / `ESCALATE` on failure) — no simulated frontend timers.
- **TALOS never merges anything** — no merge/auto-merge/approve code path exists anywhere in this phase.
- Dashboard's "Awaiting Review" metric is now real: count of `PullRequest` rows with `status="delivered"` and `github_status="open"`.
- New "TALOS Pull Requests" section on the Repository Detail page — compact history of every delivered PR with its live OPEN/MERGED/CLOSED badge, linking out to GitHub.

**Key files:** `backend/app/services/delivery_service.py` (new), `backend/app/services/github_service.py` (added `get_branch`/`find_pull_request_by_head`/`create_pull_request`/`get_pull_request`), `backend/app/services/git_workspace_service.py` (added `push_branch`/`get_current_branch`/credential stripping), `backend/app/models/future.py` (`PullRequest` model completed, `PatchAttempt.base_sha` added), `backend/app/schemas/delivery.py` (new), `frontend/src/components/{IssueDetailModal,PullRequestCard}.tsx`, `frontend/src/pages/RepositoryDetailPage.tsx`.

**Verified against the real demo repository** (`safwanshk11/talos-demo-vulnerable-app`), through the actual API — not a mock:
- Delivered job #14 (the axios patch verified in Phase 4): produced real PR [`#1`](https://github.com/safwanshk11/talos-demo-vulnerable-app/pull/1) — `head=talos/fix-3-axios`, `base=main`, commit `b72d12e...` confirmed byte-identical to the commit Phase 4 verified (no new commit created). PR body's verification table showed `SECURITY_AUDIT: FAILED` truthfully (an unrelated optional check) alongside `Original Vulnerability: REMOVED` — not smoothed over.
- **Idempotency**: called deliver on the same job twice — second call returned the identical PR #1, no duplicate created.
- **Negative test**: called deliver directly against a `patch_ready` job and a `verification_failed` job — both rejected with `400 DELIVERY BLOCKED` by the backend itself.
- **UI**: rebuilt containers, confirmed via Playwright — pipeline tracker shows all six steps including `DELIVERING` as complete, "Delivered." banner with a working "View on GitHub" link, footer copy updated, Repository Detail page's "TALOS Pull Requests" section shows PR #1 with a live `OPEN` badge, dashboard "Awaiting Review" reads `1`. Zero console errors.

**Bugs found and fixed while building this phase:**
- **Credential leak into the Phase 4 sandbox**: `git clone` (Phase 3) embeds the GitHub token directly in the cloned workspace's `.git/config` (`https://x-access-token:TOKEN@github.com/...`), and Phase 4's `SandboxService` mounts the *entire* `talos_workspaces` volume — including every workspace's `.git/config` — read-write into every verification container. This directly violated Phase 4's own "no secret ever reaches the sandbox" guarantee. Confirmed live: an already-existing workspace on disk had the real PAT sitting in its `origin` remote URL. Fixed by stripping credentials from the origin remote immediately after clone (`GitWorkspaceService._strip_credentials`) and by making the Phase 5 `push_branch` pass the credentialed URL directly as a one-off `git push` argument, never persisting it to `.git/config`. Existing at-risk workspaces were sanitized in place.
- The original `PullRequest` model (declared in Phase 1 as a placeholder, never used) had `pr_number`/`pr_url`/`branch_name`/`title` as `NOT NULL`, which doesn't fit a resumable multi-step delivery pipeline where those fields are unknown until later steps succeed — widened non-destructively (`ALTER COLUMN ... DROP NOT NULL`) rather than dropping and recreating the table.

**Known limitations:**
- `SandboxService` still mounts the whole shared `talos_workspaces` volume (not just the current job's subdirectory) into each verification container — sibling workspaces' *source code* remains visible to a running sandbox, even though the credential leak specifically is now closed. A per-job volume or Docker's `volume-subpath` mount (Engine 25+) would close this fully; deferred as a larger infra change outside this phase's scope.
- `refresh-status` (real GitHub OPEN/MERGED/CLOSED sync) is on-demand only — no background poller, per the spec's explicit "don't delay core PR creation for this" guidance.
- No idempotency at the database level (e.g. a unique constraint on `maintenance_job_id`) — duplicate-prevention is enforced in `DeliveryService`, consistent with how this codebase already handles similar invariants (e.g. `PatchAttempt.attempt_number`) rather than introducing new DB-level constraints.

---

## Phase 6 — UI/UX Overhaul + Autonomous Operations Dashboard ✅ Complete

**Goal:** Turn TALOS from a set of working pages into a coherent autonomous-operations control center — a genuine visual identity, plus a real cross-repository view of everything TALOS is doing or has done, built entirely from data the backend already produces.

**Delivered — Visual system rewrite:**
- Full near-black design-token rewrite (`tailwind.config.js`, `index.css`) replacing the old blue-tinted dark theme.
- A real marketing landing page (`LandingPage.tsx`) and a login page (`LoginPage.tsx`) built on TALOS's existing GitHub OAuth/PAT flow — no fake auth introduced.
- Authenticated app shell (`layouts/AppShell.tsx`) with sidebar navigation, replacing the single flat dashboard route.
- A small shared UI kit (`components/ui/`: `PageHeader`, `SectionCard`, `StatusBadge`, `EmptyState`, `Modal`, `Tabs`, `PageTransition`, `AnimatedNumber`, `Reveal`) so every page shares one visual language instead of ad hoc markup.
- Framer Motion throughout: route transitions, scroll reveals, a sliding shared-element active-tab/active-nav indicator, and modal exit animations (mirrored local state so content survives the close transition) — gated behind `useReducedMotion`.

**Delivered — Autonomous Operations Dashboard:**
- **Command Center** (`CommandCenterPage.tsx`) rebuilt around STATUS / ATTENTION / **Active Operations** / Recent Outcomes / **Repository Health**, aggregated client-side via `Promise.all` across existing per-repo endpoints — no new backend endpoints for read-only rollups.
- **Live job-state updates via polling** (`hooks/usePolling.ts`, 8s interval, only while something is actually active) — the honest choice given no SSE/WebSocket infrastructure exists; no fabricated progress bars.
- **Job Detail restructured into tabs** (Overview / Analysis / Patch / Verification / Delivery / Activity, via `components/ui/Tabs.tsx`) inside `IssueDetailModal.tsx` — a tab only appears once its backing data actually exists. Surfaced `analysis.root_cause` and AI provider/model, both previously fetched but never shown.
- **Maintenance Bay** (`MaintenanceBayPage.tsx`) — the 8-state filter set from the spec, plus live search.
- **Review Queue** (`ReviewQueuePage.tsx`) — the human PR handoff surface: real `PullRequest` rows with live GitHub OPEN/MERGED/CLOSED status, on-demand "Sync Status" wired to the existing Phase 5 refresh endpoint, plus search.
- **Activity Log** (`ActivityPage.tsx`) rebuilt on real cross-repository `ActionLog` records (replacing previously hardcoded fake entries) with step/failure filter chips and search.
- **Sidebar badges** (`Sidebar.tsx`) show real Maintenance Bay / Review Queue counts from the existing stats endpoint — never invented numbers.
- **Settings** (`SettingsPage.tsx`) gained an AI Provider section sourced from a small, secret-free addition to `/health` (`ai_provider`, `ai_model`).
- Lightweight client-side search added across all list pages (Repository Registry, Maintenance Bay, Review Queue, Activity Log).

**Key files:** `frontend/src/layouts/AppShell.tsx`, `frontend/src/pages/{LandingPage,LoginPage,CommandCenterPage,RepositoryRegistryPage,MaintenanceBayPage,ReviewQueuePage,ActivityPage,SettingsPage,RepositoryDetailPage}.tsx`, `frontend/src/components/ui/*`, `frontend/src/components/IssueDetailModal.tsx`, `frontend/src/hooks/{useCrossRepoData,useDashboardStats,usePolling}.ts`, `frontend/src/lib/statusGroups.ts`, `frontend/tailwind.config.js`, `frontend/src/index.css`, `backend/app/api/v1/health.py` (AI provider fields), `backend/app/schemas/repository.py` + `backend/app/api/v1/repositories.py` (`last_scanned_at` fix, below).

**Bugs found and fixed while building this phase:**
- `patch_service.py` threw an unhandled 500 when "Prepare Fix" was run against an issue whose target package had already been fixed upstream (no file changes to diff). Fixed by re-querying OSV for the real installed version before failing (`_is_still_vulnerable`/`_resolve_installed_version`); a genuinely-already-fixed issue now resolves cleanly (`job.status="resolved"`, `issue.status="RESOLVED"`) instead of crashing.
- `RepositoryDetailPage.tsx` never filtered `RESOLVED`/`DELIVERED` issues out of its active-issues list — old, already-handled issues kept showing as if still open. Fixed with an explicit `activeIssues` filter.
- `StatusBadge`'s tone mapping put bare `'OPEN'` in the success/green group, which visually implied a still-open HIGH-severity issue was resolved. Moved to the warning group. Caught during this phase's own visual QA, not user-reported.
- `Repository.last_scanned_at` was correctly written to the DB by `scanner_service.py` since Phase 2 but was never included in `RepositoryResponse` or `_to_repository_response()` — the UI had shown "Never" regardless of real scan history since Phase 1. Fixed by wiring the field through the schema and response mapper; confirmed via API and a rebuilt screenshot showing a real relative timestamp.

**Verified:** `tsc`/`vite build` clean; Playwright pass across every page and the tabbed job-detail modal with zero console errors. Confirmed the demo repository's dependencies are now genuinely at 0 vulnerabilities (cumulative effect of the real PRs delivered in Phase 5 testing) — Maintenance Bay correctly renders its real empty state rather than stale cards, and the scanner's dedup logic was confirmed not to clobber an already-`DELIVERED` issue back to `RESOLVED`. Job Detail tabs verified against a real `DELIVERED` issue (express, job with a full patch/verification/PR trail): Overview showed real metadata plus risk/status/created-at; Verification tab rendered the actual `VerificationReport` — sandbox ID, per-check PASS/SKIPPED with real durations, `Original Vulnerability: PASS — express 4.17.1 → 5.2.1: advisory GHSA-qw6h-vgh9-j6wx removed`.

**Known limitations:**
- Live updates are polling, not push (see [Cross-Phase Technical Debt](#cross-phase-technical-debt-tracked-not-yet-addressed) — no SSE/WebSocket infra exists; introducing it wasn't justified for this phase alone).
- "Active Operations" descriptions reflect only real, already-fetched job state (e.g. `VERIFYING`) — no fabricated blow-by-blow narrative ("Running security audit...") since that granularity isn't available without expensive extra fetches.
- PR status sync in Review Queue is manual (button), not automatic on load — consistent with Phase 5's own "don't delay core delivery for this" precedent.

## Phase 6.5 — Decision Engine & Autonomy Governance ✅ Complete

**Goal:** Answer the question Phases 1–6 left open — *who decides whether TALOS should act in the first place?* Turn TALOS from an automated pipeline that runs whenever a human clicks "Prepare Fix" into a policy-governed autonomous operator that decides, per issue, whether to act on its own, ask first, refuse, or defer to a human.

**Delivered:**
- **`DecisionEngine`** (`backend/app/services/decision_service.py`) — a pure, deterministic function with no AI/network call. Evaluates a `DecisionInput` (repository state, issue, policy, patch risk/files, verification capability, conflicts) against a fixed precedence order — hard safety rules → protected paths → user policy → risk → verification capability — and returns one of `AUTO_EXECUTE` / `PREPARE_ONLY` / `APPROVAL_REQUIRED` / `ESCALATE` / `IGNORE` / `BLOCKED_BY_CONFLICT`, each with a human-readable reason and the exact rule names that matched. AI (Ollama/Gemini) only ever supplies structured input (risk classification, files touched) — it never gets a vote on whether autonomous action is safe.
- **`RepositoryAutomationPolicy`** (new table, one row per repository) — three presets (**Conservative** / **Balanced** *(default)* / **Autonomous**) covering security patches, patch/minor/major dependency updates, and protected-path handling. Major-update and protected-path actions can never be set to `AUTO_EXECUTE`, enforced server-side in `PolicyService.update()`, not just hidden in the UI.
- **Protected paths**: deterministic glob matching (`**/auth/**`, `**/payments/**`, `**/migrations/**`, `**/infrastructure/**`, `.github/workflows/**` by default, user-editable) against the AI plan's actual `files_to_modify` — never inferred from repository content, so a malicious README can't talk TALOS into anything (policy comes only from the trusted DB row).
- **Two-pass evaluation in `PatchService.prepare_fix`**: a cheap pre-flight pass (repository paused, duplicate active job, existing open PR) runs *before* any clone/AI cost is spent; a full pass runs after the plan and risk are known, now also checking protected paths and the policy tier for the classified update type (`SECURITY_PATCH` / `PATCH_DEPENDENCY_UPDATE` / `MINOR_DEPENDENCY_UPDATE` / `MAJOR_DEPENDENCY_UPDATE`, the last three via real semver comparison).
- **`AUTO_EXECUTE` genuinely chains the pipeline**: patch → verify → deliver in one continuous run (still fully synchronous, no new worker infra), gated the whole way by Phase 4/5's existing hard checks — TALOS still never merges. `PREPARE_ONLY` stops at `patch_ready`, matching the pre-6.5 default behavior.
- **`APPROVAL_REQUIRED` is a real pause, not a suggestion**: TALOS persists the exact `analysis`/`plan` it already produced (never regenerated) on a `PatchAttempt(status="awaiting_approval")` row and stops. A new `POST .../jobs/{id}/approve` resumes that exact artifact through patch → verify → deliver; `POST .../jobs/{id}/reject` cleans up the workspace and marks the issue `REJECTED_BY_USER`. Both endpoints re-validate `job.status == "waiting_for_approval"` server-side — there is no separate "patch endpoint" to bypass, since `prepare_fix` re-runs the same conflict check on every call and would immediately re-block a duplicate attempt on an issue already awaiting approval.
- **Collision handling**: one active patch job per repository (a deliberately simpler alternative to file-level locking, per the phase's own guidance) — a second `prepare-fix` call while one is in flight gets `BLOCKED_BY_CONFLICT` with the specific conflicting job ID stored on `MaintenanceJob.blocking_job_id`.
- **Real Action Ledger entries**, not a badge: every decision logs its policy, every rule it evaluated, and the final decision with reason — visible in the repository's real Activity feed.
- **UI**: a new **Decision** tab on the Job Detail modal (matched policy, risk, full reasoning, matched rules, blocked-by); an amber "Developer Approval Required" banner with real **Approve & Continue** / **Reject** actions; distinct banners for `BLOCKED_BY_CONFLICT` / `IGNORED` / `REJECTED_BY_USER`; a new **Autonomy Policy** section on the Repository Detail page (mode presets, four tier dropdowns, protected-path list with add/remove). `APPROVAL_REQUIRED` issues now surface in Command Center's "Needs Attention" for free, since it's added to the shared `ATTENTION_STATUSES` group.

**Key files:** `backend/app/models/policy.py` (new), `backend/app/services/decision_service.py` (new), `backend/app/schemas/policy.py` (new), `backend/app/services/patch_service.py` (restructured: pre-flight + full decision integration, `_finalize_patch`/`_auto_chain`/`resume_after_approval`/`reject`), `backend/app/api/v1/repositories.py` (`/automation-policy`, `/jobs/{id}/approve`, `/jobs/{id}/reject`), `backend/app/models/future.py` (decision columns on `MaintenanceJob`), `frontend/src/components/IssueDetailModal.tsx`, `frontend/src/pages/RepositoryDetailPage.tsx`, `frontend/src/lib/statusGroups.ts`, `frontend/src/components/ui/StatusBadge.tsx`, `frontend/src/types/index.ts`, `frontend/src/services/api.ts`.

**Tests:** `backend/tests/test_decision_engine.py` — 12 unit tests against the pure `DecisionEngine.evaluate()`, covering all 7 cases the phase's own spec requires (low-risk security patch → `AUTO_EXECUTE`; major update → `ESCALATE`; protected path → `APPROVAL_REQUIRED`; paused repository → blocked; existing open PR → no duplicate; conflicting active job → `BLOCKED_BY_CONFLICT`; verification-failed → no delivery, already enforced by Phase 5's existing hard gate) plus medium-risk downgrade, same-issue-vs-repo-lock precedence, semver bump classification, and glob matching. All 17 backend tests (12 new + 5 pre-existing) pass; `tsc`/`vite build` clean.

**Verified live** against the running stack (not just unit tests): paused repository 1 and called `prepare-fix` on a real issue — response in 32ms with `decision: "IGNORE"`, `blocked_by: ["REPOSITORY_PAUSED"]`, and zero clone/AI cost incurred; confirmed via `GET /automation-policy` that a fresh repository correctly auto-provisions the `BALANCED` preset with the five default protected paths; confirmed via Playwright (zero console errors across Command Center, Maintenance Bay, Review Queue, Activity Log, Repository Detail, and the Job Detail modal) that the real `DECIDE` ledger entries from that test flow into the existing Activity/Recent Outcomes UI, and that the Decision tab renders the real matched-rules/blocked-by data. Repository monitoring was restored to `active` afterward.

**Known limitations:**
- `AUTO_EXECUTE`'s patch→verify→deliver chain runs synchronously inside the `prepare-fix` HTTP request (consistent with this codebase's existing architecture, which has no worker/queue infra) — a single request can now take noticeably longer end-to-end. Introducing async job execution was judged out of scope for this phase.
- A live end-to-end `AUTO_EXECUTE`/`APPROVAL_REQUIRED` demo through a fresh real vulnerability wasn't captured in this pass, because the demo repository (`talos-demo-vulnerable-app`) is already fully patched from prior phase testing (0 open issues) — reintroducing a vulnerability would mean pushing a commit to that live GitHub repo, which wasn't done without being asked. The pre-flight `IGNORE` path was verified live instead (see above); the full post-plan decision path (protected paths, risk tiers, `AUTO_EXECUTE` chaining) is covered by the unit test suite but not yet re-confirmed against a live AI-generated plan in this session.
- Collision handling is a repository-level lock, not file-level — intentional per the phase's own MVP guidance ("prefer reliability over concurrency").

## Phase 7 — Continuous Autonomous Monitoring & Event-Driven Maintenance ✅ Complete

**Goal:** Remove the requirement that a developer must keep the TALOS UI open and click buttons for anything to happen. TALOS should watch continuously and act selectively — without ever bypassing Phase 6.5's governance or inventing a second autonomous pipeline.

**Delivered:**
- **`MonitoringOrchestrator`** (`backend/app/services/monitoring_service.py`) — the only new orchestration logic in this phase. It decides *whether and when* to invoke the existing, unmodified pipeline (`ScannerService.run_repository_scan()` → `PatchService.prepare_fix()`, both of which already do full Decision-Engine-gated AUTO_EXECUTE/APPROVAL_REQUIRED/ESCALATE handling from Phase 6.5) — it never reimplements any of it.
- **GitHub webhook intake** (`POST /api/v1/webhooks/github`): `X-Hub-Signature-256` verified via HMAC-SHA256 against a configured secret before any processing — no secret configured means every request is refused (503), never silently accepted unverified. Handles `push` (relevance-filtered scan trigger) and `pull_request` (close/merge syncs `PullRequest.github_status` back from real GitHub state).
- **Relevance filtering**: a push only triggers a scan if it touches a maintenance-sensitive file (`package.json`, lockfiles, `requirements.txt`, etc.) on the repository's default branch — a docs-only push costs nothing.
- **Scheduled monitoring**: an `asyncio` background task inside the existing FastAPI process (no Celery/Redis/cron daemon — matches this codebase's established "simplest reliable mechanism" precedent from Phase 6's polling) — ticks periodically and scans any repository whose `monitoring_schedule` (manual/daily/weekly, opt-in per repository) is due.
- **Event idempotency**: `RepositoryEvent.delivery_id` (GitHub's `X-GitHub-Delivery`) checked before any processing — a retried webhook delivery is acknowledged and ignored, never turned into a second scan.
- **Issue identity — reused, not rebuilt**: Phase 2's fingerprint-based dedup already did exactly what this phase needed (the same vulnerability across five scans stays one issue, auto-resolves when it disappears).
- **TALOS self-trigger loop prevention**: pushes to `talos/fix-*` branches (TALOS's own patch branches) are recognized and skipped before any processing — confirmed live, not just unit-tested.
- **Concurrency preserved**: `MonitoringOrchestrator` reuses Phase 6.5's one-mutating-workflow-per-repository philosophy (`has_active_scan()`/`has_active_job()`) rather than building new locking.
- **Provenance everywhere**: `MaintenanceJob.trigger` / `RepositoryScan.trigger` (`manual`/`scheduled_scan`/`github_push`), visible in the Job Detail Overview tab and the real Action Ledger (e.g. *"Autonomous cycle started (trigger=github_push)."*) — never a fabricated narrative.
- **UI**: Command Center gained a "System Status" line (repositories monitored/paused, next scheduled check) computed entirely from data already fetched — no new rollup endpoint. Repository Detail gained a compact **Monitoring** section (schedule, relevant-push toggle, last automatic scan, last trigger), respecting the existing pause/resume switch as the authoritative on/off control everywhere.

**Key files:** `backend/app/models/monitoring.py` (new `RepositoryEvent`), `backend/app/services/monitoring_service.py` (new — `EventService`, `MonitoringOrchestrator`, `SchedulerService`), `backend/app/api/v1/webhooks.py` (new), `backend/app/schemas/monitoring.py` (new), `backend/app/models/repository.py` (`monitoring_schedule`/`scan_on_relevant_push`/`last_automatic_scan_at`/`last_trigger`), `backend/app/services/scanner_service.py` + `patch_service.py` (added `trigger` parameter only — pipelines themselves untouched), `backend/app/main.py` (scheduler task lifecycle, startup reconciliation), `frontend/src/pages/{CommandCenterPage,RepositoryDetailPage}.tsx`.

**Bugs found and fixed while building this phase:**
- **Orphaned "running" scans blocking all future autonomous work**: two scans from early in this project's development had been left in `status="running"` forever by an earlier container restart (the existing scanner's exception handler can't run if the process itself is killed mid-scan — a latent gap since Phase 2). This was invisible before Phase 7 because nothing previously queried for "is a scan active" — the new `has_active_scan()` concurrency lock (built for exactly this phase's collision-safety requirement) surfaced it immediately by treating that repository as permanently busy. Fixed with a startup reconciliation pass: any scan/job left mid-flight by a previous process life is marked `failed` and diagnosable, never silently stuck.

**Verified live against the running stack** (webhook calls with real, correctly-computed HMAC signatures against the actual deployed backend — not mocked):
- **Relevant push**: a signed push touching `package.json`/`package-lock.json` → real clone, real OSV scan (`triggered_scan_id` recorded), honestly found 0 open issues (the demo repo's actual current state) — `Repository.last_trigger` correctly updated to `github_push`.
- **Irrelevant push**: a signed push touching only `README.md` → `skipped: no_relevant_file_changes`, no scan spent.
- **Loop prevention**: a signed push to `talos/fix-3-axios` → `skipped: talos_generated_branch`.
- **Idempotency**: the same delivery ID posted twice → second call returns `duplicate_ignored`.
- **Signature enforcement**: an invalid signature → `401`; no secret configured → `503`, in both cases before any payload processing.

**Tests:** `backend/tests/test_monitoring.py` — 18 new tests (signature verification, TALOS-branch/relevance pure functions, scheduler due-check logic across manual/daily/weekly, and 6 real webhook-endpoint tests via `TestClient` against a live DB). 35/35 backend tests pass together.

**Known limitations:**
- No live scheduled-scan demo captured (would require a 24h wait or direct DB timestamp manipulation) — the due-check logic itself is unit-tested instead of observed firing in real time.
- **Deliberately defaulted `monitoring_schedule` to `manual`, not the spec's suggested `daily`** — this connects to real, already-live GitHub repositories (including this project's own repository), and a newly-shipped background scheduler should not start autonomously scanning/patching them the moment it ships without the owner opting in per repository.
- Real GitHub webhook delivery end-to-end (GitHub itself calling TALOS) is untestable from this local Docker Compose environment without a public URL (e.g. ngrok) — verified instead via correctly-signed simulated payloads against the live backend, which exercises the identical code path a real delivery would.
- The `AUTO_EXECUTE` continuation (patch → verify → deliver) triggered by an autonomous cycle wasn't re-demonstrated fresh in this phase's live testing, because the demo repository currently has 0 open issues; it's unmodified from Phase 6.5, where it was already verified.

---

## Phase 8 — Production Hardening + Hackathon Polish 🔜 Planned

Real multi-tenant auth, encrypted secret storage (GitHub PAT is currently plaintext — see Phase 1), formal DB migrations (currently ad-hoc `ALTER TABLE` statements — see Phase 1/2), broader ecosystem support, general robustness pass.

---

## Cross-Phase Technical Debt (tracked, not yet addressed)

- **No formal migration tooling.** Alembic is an installed dependency but unused; schema changes are applied via `ADD COLUMN IF NOT EXISTS` statements in `main.py`'s startup lifespan. Safe so far because every affected table has been empty at the time of change, but this will not scale past a certain point.
- **GitHub PAT stored in plaintext** (`github_connections.access_token`).
- **Single-user local-dev auth** — no real multi-tenancy yet.

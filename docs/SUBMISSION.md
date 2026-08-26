# TALOS — BYAMN Buildathon 2026 Submission Materials

Copy-paste-ready content for the submission form, pitch, and demo video
script. Everything below reflects what the codebase actually does — verified
by a fresh code audit in Phase 9, not carried forward from earlier phase
claims. Where a URL isn't known yet, it's left as an explicit placeholder.

---

## 1. Project Name

**TALOS**
*Autonomous Repository Maintenance*

(No forced acronym — the name predates any backronym and none reads better than the plain name.)

## 2. Tagline

Primary (branding):
> **Autonomous maintenance. Human control.**

Conversational:
> **TALOS does the maintenance. You review the pull request.**

## 3. Final Project Description

> TALOS is a policy-governed autonomous repository maintenance platform that continuously monitors software repositories, identifies actionable maintenance issues, evaluates whether autonomous action is safe, prepares code changes, verifies them through deterministic engineering checks, and delivers review-ready GitHub pull requests — while keeping the final merge under human control.

## 4. Problem Statement

> Software teams spend recurring engineering time identifying dependency issues, understanding their impact, preparing fixes, running verification, and creating pull requests. Existing automation often handles only parts of this workflow — surfacing an advisory without preparing the fix, or generating a change without proving it works — and still requires a developer to initiate and supervise the work. TALOS turns repository maintenance into a governed autonomous workflow while preserving human control over the final merge.

## 5. Solution Statement

> TALOS connects to GitHub repositories, continuously monitors them for actionable maintenance issues, evaluates each issue against repository policy and risk through a deterministic Decision Engine, prepares permitted fixes using AI for the parts that genuinely require semantic reasoning, verifies those changes through real build/test/security checks inside an isolated sandbox, and creates a pull request only after the patch earns it.

## 6. 10-Second Pitch

> TALOS is an autonomous repository maintenance agent that detects maintenance work, decides whether it's safe to act, verifies its own fixes, and delivers review-ready pull requests.

## 7. 30-Second Pitch

> Developers lose time repeatedly handling repository maintenance — identifying issues, understanding impact, preparing fixes, testing them, and creating pull requests. TALOS turns that into a governed autonomous workflow. It monitors repositories, detects actionable maintenance, decides whether it's safe to act, prepares the change, verifies it using real engineering checks, and creates a pull request only when those checks pass. TALOS handles the repetitive work; the developer keeps control of the final merge.

## 8. Final Feature List

- Continuous repository monitoring (scheduled + GitHub webhook–triggered)
- Maintenance issue detection (real OSV vulnerability queries + dependency parsing)
- Policy-governed Decision Engine (`AUTO_EXECUTE` / `APPROVAL_REQUIRED` / `ESCALATE` / `IGNORE` / `BLOCKED_BY_CONFLICT`)
- Per-repository automation policy (Conservative / Balanced / Autonomous presets, protected paths, tier overrides)
- AI-assisted patch planning (Ollama local / Gemini deployment) + deterministic patch application
- Sandboxed, no-secrets Docker verification (build/test/security-audit/original-issue re-scan)
- Human approval & escalation workflow, enforced server-side
- Real GitHub pull request delivery with artifact-integrity hash gating
- Action Ledger (full audit trail, every pipeline step)
- Autonomous Operations Command Center, Maintenance Bay, and Review Queue

## 9. Actual Tech Stack

*(generated from the repository, not guessed)*

- **Frontend**: React 18, TypeScript, Vite, React Router v6, Framer Motion, Lucide Icons, Tailwind (custom near-black design system)
- **Backend**: FastAPI, Python 3.11, async SQLAlchemy 2.0, Pydantic v2, HTTPX
- **Database**: PostgreSQL 16
- **AI providers**: Ollama (local dev) or Google Gemini (deployment) behind a pluggable `AIProvider` interface — no mock/stub provider exists in the code
- **Verification sandbox**: docker-outside-of-docker — the backend launches isolated, ephemeral, no-secret containers on the host's own Docker engine
- **Scheduling / background work**: an `asyncio` background task inside the existing FastAPI process — **no Redis, no Celery, no separate job queue or worker service**. This is a deliberate architectural choice for a single-instance deployment, not an omission — see Known Limitations.
- **Delivery**: real GitHub REST API pushes + pull request creation — no automatic merge, ever
- **Containerization**: Docker & Docker Compose, both images with real production builds and healthchecks

## 10. Architecture Summary

```text
GitHub ──(OAuth + Webhooks)──► TALOS Frontend (React, production build)
                                        │  /api proxy
                                        ▼
                                TALOS Backend (FastAPI)
                                   │            │
                                   ▼            ▼
                              PostgreSQL   asyncio background task
                                            (scheduler + workspace reaper —
                                             no Redis/queue/worker service)
                                   │
                                   ▼
                    docker-outside-of-docker ──► ephemeral, no-secret
                    (host socket mount)           verification sandbox
                                   │
                                   ▼
                          Decision Engine (deterministic, no AI)
                                   │
                                   ▼
                          AI Provider (Ollama/Gemini) — plan/analysis only
                                   │
                                   ▼
                             Real GitHub Pull Request
```

The single-process, no-queue architecture is intentional: every phase of
this project reused existing infrastructure rather than adding new services,
and the resulting system is correct and reliable for a single backend
instance. It does not horizontally scale past one instance without adding
real queue infrastructure — documented honestly, not hidden.

## 11. AI Disclosure

**AI used to build TALOS:** Claude (Anthropic), via Claude Code, throughout the project's development — architecture, implementation, debugging, and the audits behind the Phase 8/9 hardening passes.

**AI used inside TALOS at runtime:** a pluggable `AIProvider` interface with exactly two real implementations — **Ollama** (local models, local development) or **Gemini** (Google's API, deployment). The model only *analyzes* a detected issue and *proposes* a structured fix plan — it never executes code, never decides whether a fix is safe to apply autonomously (that's the separate, deterministic Decision Engine), and never hand-writes a dependency version bump — actual version changes go through deterministic package-manager operations (`npm install --package-lock-only`, a real PyPI lookup + regex rewrite for `requirements.txt`), not model-generated file contents.

## 12. Core Differentiators

**Policy-governed autonomy** — TALOS evaluates whether it's permitted to act, with the check enforced server-side, before modifying repository code.

**Deterministic verification** — generated patches must pass real build/test/security-audit checks inside an isolated sandbox before delivery; a failed check means no PR, not a lower-confidence PR.

**Continuous operation** — connected repositories can be monitored through scheduled checks and real, signature-verified GitHub webhook events, without a human keeping the UI open.

**Human-controlled delivery** — TALOS creates verified pull requests. Humans retain merge authority, unconditionally, in every configuration.

*(Not claimed as globally unprecedented — the honest claim is the integrated closed loop: detect → evaluate autonomy → execute → verify → deliver → escalate when necessary, not any single piece in isolation.)*

## 13. Judge Q&A Prep

**"Why not just use Dependabot?"**
> Dependabot surfaces an advisory and can open a PR with a version bump — TALOS goes further: it evaluates whether autonomous action is even appropriate for a given change (risk tier, protected paths, repository policy), applies the fix, and proves the fix actually works (build/test/security-audit/re-scan) before opening the PR. It's a different point in the pipeline — Dependabot detects, TALOS detects, decides, fixes, and proves.

**"What if the AI generates bad code?"**
> The AI never gets to decide whether its own output ships. A patch is marked `VERIFIED` only if every real check genuinely passes inside an isolated, no-secrets Docker sandbox, and delivery re-checks that the verified artifact's hash still matches what's about to be pushed. If verification fails, there's no PR — that's not a fallback path, it's the only path.

**"What stops TALOS from touching sensitive code?"**
> The Decision Engine evaluates protected paths and risk classification before any patch is applied — a change touching a protected path or classified as HIGH risk cannot be `AUTO_EXECUTE`, full stop, enforced server-side (a direct API call can't bypass it either).

**"What if tests don't exist in the target repo?"**
> Repository readiness is scored (build/test/CI signals present or not) and factored into the Decision Engine — lower readiness reduces what TALOS is willing to do autonomously rather than pretending the missing signal doesn't matter.

**"Does TALOS merge code?"**
> No. Never, under any configuration. TALOS opens a pull request; a human merges it.

**"What happens if verification fails?"**
> No delivery. The job's real status (`verification_failed`) is shown honestly, including which specific check failed — this exact scenario has happened for real in this project's own demo repository history, not just in a unit test.

**"Does this run automatically, or does someone have to click a button?"**
> Both are real. A developer can trigger a scan/fix manually, and — separately — TALOS can also detect and act on its own via a scheduled check or a GitHub webhook (signature-verified), with the same Decision Engine governing both paths identically.

**"Where is AI actually used?"**
> Semantic analysis and patch planning — deciding *what* a fix should look like when it requires understanding code, not just bumping a version number. Policy, risk classification, verification, and delivery are all deterministic, non-AI logic; the AI never controls whether something ships.

**"How do you prevent prompt injection from a malicious repository?"**
> Repository content (README text, source comments, issue text) is treated as untrusted data fed into context for analysis — it cannot alter TALOS's policy, decision logic, or verification requirements, which live entirely outside the AI's control and are evaluated independently of anything the model outputs.

**"Is this multi-tenant / production auth?"**
> Honestly, not yet — the current build is single-tenant (one implicit local account per deployment, with real GitHub OAuth/PAT verification gating access to it). Authorization *within* that account is enforced correctly (every query is scoped), but multi-user support is future work, not shipped today.

---

## 14. Demo Script (2:20–2:45 target)

**Story beat:** MONITOR → DETECT → DECIDE → PATCH → VERIFY → DELIVER → HUMAN REVIEW, told through one repository, `safwanshk11/talos-demo-vulnerable-app`, which has real prior history to fall back on if live steps are slow or flaky. **Currently armed and ready**: `lodash@4.17.15` (a known prototype-pollution CVE, deliberately a *different* package from the `axios`/`express` already fixed in merged PRs `#1`-`#3` — see `docs/DEMO_RESET.md`) was introduced, and a live scan already confirmed fresh detection (6 real OSV advisories, `axios` unaffected/clean). The Decide → Patch → Verify → Deliver steps have deliberately not been pre-run, so they're available to perform live. If the demo has already been run once since, re-run `docs/DEMO_RESET.md`'s steps with a not-yet-used package next time.

| Time | Beat | What to show |
|---|---|---|
| 0:00–0:15 | Problem + TALOS | Landing page — "Autonomous maintenance. Human control." |
| 0:15–0:30 | Command Center | Repos monitored, open issues, active jobs, PRs ready — don't explain every card |
| 0:30–0:50 | Detected issue | Open the demo repo → a real detected vulnerability (`lodash`, HIGH severity, real installed vs. recommended version) |
| 0:50–1:10 | Decision Engine | Job Detail → Decision tab: `AUTO_EXECUTE`, with the real evaluated rules (patch-level update, low risk, readiness sufficient, no protected paths, no conflict) |
| 1:10–1:35 | Patch | Real diff — files changed, dependency bump, isolated branch, primary branch untouched |
| 1:35–2:00 | Verification | Real build/test/security-audit results, PASS/FAIL/SKIPPED shown honestly — never claim a SKIPPED check as PASS |
| 2:00–2:20 | Delivery | Real GitHub PR — open it live, show the real branch/commit/diff/verification summary in the description |
| 2:20–2:35 | Safety boundary | One refusal case: a protected-path or HIGH-risk change → `ESCALATE` → "TALOS modified 0 files." Keep this to a few seconds. |
| 2:35–2:45 | Closing | "TALOS does the maintenance. You review the pull request." |

**If live steps are slow:** narrate over the wait using the Decision Engine / verification / safety explanation rather than sitting in silence — the spec's own guidance, and genuinely useful since a real Docker-sandboxed verification run takes real seconds, not zero.

**Fallback if something breaks live:** navigate to the demo repository's existing, already-merged PRs (`#1`, `#2`, `#3` on `talos-demo-vulnerable-app`) and the Job Detail history behind them — this is real evidence of the full pipeline having worked end-to-end multiple times, not a staged backup.

## 15. Video Title

> TALOS — Autonomous Repository Maintenance | BYAMN Buildathon 2026

## 16. Known Limitations (submission-facing summary)

- Single-tenant auth: one implicit local account per deployment (real GitHub OAuth/PAT verification gates access to it; no multi-user support yet).
- No Redis/queue/worker service — scheduling and monitoring run as an in-process `asyncio` task; correct for one backend instance, doesn't horizontally scale.
- No formal DB migration tooling (Alembic installed but unused; schema evolves via idempotent `ADD COLUMN IF NOT EXISTS`).
- GitHub PAT stored in plaintext, not encrypted at rest.
- Live job cancellation is unavailable once a job is running.
- Autonomous repair retries are intentionally limited — a failure is reported honestly rather than silently retried.
- npm has the strongest deterministic security-audit coverage; other ecosystems' coverage depends on what that ecosystem's own tooling reports.
- The verification sandbox has outbound internet access (needed for `npm install`/`pip install`) — isolated from TALOS's own services, not from the public internet.
- TALOS creates pull requests but never merges them, under any configuration — permanent, not a current-version gap.

## 17. Future Work

- Additional package ecosystems beyond npm/pip
- Broader maintenance categories beyond dependency/security issues
- Real multi-tenant authentication and authorization
- Organization-level policy management
- Additional verification adapters (more languages/frameworks)
- Developer notification integrations (Slack/email)

---

## Placeholders — fill in before submitting

- **Production URL:** _not yet deployed to a public host — currently runs via local Docker Compose only. See PHASES.md Phase 8 for what a real deployment would need._
- **GitHub repository URL:** `https://github.com/safwanshk11/talos` _(confirm this is the intended public URL before submitting)_
- **Demo video URL:** _not recorded yet_
- **Live demo URL:** _same as Production URL — not yet available_

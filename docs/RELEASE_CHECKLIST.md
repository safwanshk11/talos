# TALOS Release Checklist

Status as of Phase 9 (Final Demo, Submission & Ship). Checked items were
verified live against the running stack, not just asserted — see `PHASES.md`'s
Phase 8/9 entries for exactly how each was verified. Unchecked items require
action before a real deployment or a live demo — each has a reason, not just
a checkbox.

**Phase 9 update:** a real authentication bypass was found and fixed —
`get_current_user` previously accepted any request, even with no token, as a
default local user. Now enforced correctly in `ENVIRONMENT=production`
(hard `401`), unchanged in development. See the Security section below and
`PHASES.md`'s Phase 9 entry for the live verification.

## Environment & Configuration

- [x] `.env.example` documents every setting `config.py` reads, including the
      Phase 4 verification sandbox settings and Phase 8's `WORKSPACE_RETENTION_HOURS`.
- [x] Startup configuration validation is wired in (`validate_startup_config()`,
      called first in `main.py`'s lifespan) — verified live: a fresh boot with
      no `.env` overrides logs the expected `SECRET_KEY`/OAuth warnings and starts.
- [ ] **`SECRET_KEY` changed from the published default.** Required before
      `ENVIRONMENT=production` — TALOS will refuse to boot otherwise (this is
      enforced, not just documented).
- [ ] **`ENVIRONMENT=production` set** in the real deployment's environment
      (defaults to `development`, which only warns instead of blocking).
- [ ] `GEMINI_API_KEY` set if `AI_PROVIDER=gemini` (required in production).
- [ ] `GITHUB_REDIRECT_URI` and `BACKEND_CORS_ORIGINS` updated to the real
      deployment origin, not `localhost`.

## Database

- [x] Schema initializes cleanly from empty (`Base.metadata.create_all` +
      `ADD COLUMN IF NOT EXISTS` migrations run every boot, idempotently).
- [x] Migrating against the existing development database is safe — verified
      via the live restart test (all 14 repositories / 29 jobs / 3 PRs intact
      after a real `docker compose restart backend`).
- [ ] No formal migration tool (Alembic is installed but unused) — acceptable
      for the current single-environment deployment, tracked as debt for
      anything larger. See `PHASES.md` Cross-Phase Technical Debt.

## Docker & Deployment

- [x] `docker compose build` succeeds for both images from a clean context
      (verified live, including the frontend's real `tsc && vite build`).
- [x] Both images have real `HEALTHCHECK` instructions; `docker-compose.yml`'s
      frontend waits on the backend's actual health, not just start order.
- [x] `.dockerignore` present for both images (also fixes a real bug where the
      frontend build previously overwrote container `node_modules` with the host's).
- [x] Frontend serves a real production build (`vite preview`), not the dev/HMR server.
- [x] Backend `/var/run/docker.sock` mount confirmed necessary and isolated —
      sandbox containers get zero TALOS secrets (audited every `docker run` call).
- [ ] Backend container runs as root — deliberate (docker.sock access), not fixed.
      See Known Limitations in `README.md`.

## Security

- [x] No committed secrets, no `console.log`/`debugger`/`print()` debris, no
      debug-only API routes, no mock data outside test fixtures — full audit, zero findings.
- [x] Verification sandbox confirmed to receive zero TALOS secrets on every launch.
- [x] `dependency_updater_service.py`'s npm resolution step now runs with
      secrets explicitly stripped from its environment.
- [x] No `shell=True` anywhere in the codebase; every subprocess call uses an
      argv list and has an explicit timeout.
- [x] Authorization verified: every repository-scoped endpoint filters by the
      authenticated user's ID at the service layer — a user cannot reach
      another user's repository/issue/job/PR by ID.
- [ ] GitHub PAT is stored in plaintext — not encrypted at rest. Tracked debt.

## Safety Enforcement (re-verified unchanged this phase)

- [x] TALOS never auto-merges — no configuration path changes this.
- [x] Delivery integrity gate (verified-hash vs. about-to-deliver-hash mismatch
      blocks delivery) — Phase 5 logic untouched, tests still pass.
- [x] Decision Engine / approval workflow enforced server-side, not just in
      the UI — Phase 6.5 logic untouched, all 12 decision-engine tests pass.
- [x] Paused repositories produce zero autonomous action (push event, schedule
      tick) — Phase 7 logic untouched.
- [x] TALOS recognizes and ignores pushes to its own `talos/fix-*` branches —
      Phase 7 logic untouched, previously live-verified with real signed webhooks.

## Testing

- [x] Full backend test suite passes: **35/35**, re-run after every Phase 8 change.
- [x] Live restart test: backend restarted mid-deployment, all data survived,
      scheduler resumed, no job/scan left stuck in a non-terminal state.
- [ ] Full live end-to-end run (scan → detect → decide → patch → verify →
      real PR) was **not** re-executed against a live GitHub repository this
      phase — last live-verified in Phase 6.5/7. Recommended before a demo.
- [ ] Negative safety tests (bad patch → verification fails → no PR; high-risk
      change → escalate → no patch) were **not** re-executed live this phase —
      logic unchanged since Phase 3/6.5, covered by existing unit tests only.
- [ ] Autonomous end-to-end run (webhook/schedule trigger with browser closed)
      was **not** re-executed live this phase — last live-verified in Phase 7.

## Demo Readiness

*(Updated in Phase 9 — the items below were incorrectly marked as blocked in Phase 8, which hadn't checked whether a demo repository already existed. It did.)*

- [x] **Dedicated demo repository exists and has real history**: `safwanshk11/talos-demo-vulnerable-app` — 29 real `MaintenanceJob` runs, 3 real pull requests, all merged by a human. See `PHASES.md`'s Phase 9 entry.
- [x] **Demo reset procedure documented**: `docs/DEMO_RESET.md` — how to re-arm the demo repository with a fresh, live-detectable vulnerability using dependency versions already proven through the full pipeline. Not automated as a TALOS feature, deliberately.
- [x] **Demo preflight script exists and passes**: `scripts/demo-preflight.sh` — run live, reports `READY` (8/8 checks) against the current stack.
- [ ] `GITHUB_WEBHOOK_SECRET` + a public URL (e.g. ngrok) configured, if the
      demo includes the autonomous/webhook-triggered flow. Not currently configured.
- [x] **Demo repository re-armed with user confirmation**: `lodash@4.17.15`
      introduced (commit `0d4772b`) — deliberately a different package from
      the `axios`/`express` already fixed in merged PRs `#1`-`#3`, per user
      feedback to keep each demo genuinely new rather than a repeat. `axios`
      restored to latest. A live scan confirmed 6 fresh real OSV advisories
      on `lodash`. Left at the detected stage — Decide → Patch → Verify →
      Deliver intentionally not pre-consumed, so it's available to actually
      perform live.

## Documentation

- [x] `README.md` updated: Safety Model, Deployment, Known Limitations, AI
      Disclosure sections; environment variable table current; Mermaid
      architecture/workflow diagrams; screenshots; Phase 9 status.
- [x] `PHASES.md` updated with the full Phase 8 and Phase 9 audit findings,
      fixes, and explicit known limitations.
- [x] `docs/SUBMISSION.md` — pitch, demo script, judge Q&A, submission copy.
- [x] `LICENSE` — MIT.
- [x] This checklist.

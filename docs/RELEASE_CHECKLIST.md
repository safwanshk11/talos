# TALOS Release Checklist

Status as of Phase 8 (Production Hardening & Deployment). Checked items were
verified live against the running stack during Phase 8, not just asserted —
see `PHASES.md`'s Phase 8 entry for exactly how each was verified. Unchecked
items require action before a real deployment or a live demo — each has a
reason, not just a checkbox.

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

- [ ] **No dedicated demo repository exists yet.** Needs a small, deterministic
      JS/TS (or Python) repo with a known vulnerable dependency and a known fix,
      owned by the presenter's GitHub account.
- [ ] **No demo reset script exists yet** — write one once the demo repository
      exists (reset default branch, remove old `talos/fix-*` branches, close
      stale demo PRs). Deliberately not built speculatively against a
      repository that doesn't exist.
- [ ] **No demo preflight script exists yet** — same reasoning; a preflight
      check needs a real target to check against. In the meantime, the
      manual equivalent is: `curl http://localhost:8000/api/v1/health` returns
      `200`, `docker compose ps` shows both services `healthy`, Ollama/Gemini
      reachable per `AI_PROVIDER`, and the demo repository is connected.
- [ ] `GITHUB_WEBHOOK_SECRET` + a public URL (e.g. ngrok) configured, if the
      demo includes the autonomous/webhook-triggered flow.

## Documentation

- [x] `README.md` updated: Safety Model, Deployment, Known Limitations, AI
      Disclosure sections; environment variable table current.
- [x] `PHASES.md` updated with the full Phase 8 audit findings, fixes, and
      explicit known limitations.
- [x] This checklist.

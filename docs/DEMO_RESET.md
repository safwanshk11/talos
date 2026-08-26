# TALOS Demo Reset Procedure

> **Status:** executed for real on 2026-08-26 (Phase 9), twice. First pass
> reused `axios@0.21.1` (commit `2fce190`) — but that's the same package
> already fixed in merged PRs `#1`/`#2`, so it would have made the live demo
> look like a rerun rather than new work. Corrected immediately: `axios` was
> restored to latest and **`lodash@4.17.15`** was introduced instead (commit
> `0d4772b`) — a different package, a different vulnerability class
> (prototype pollution, not axios's SSRF/ReDoS history), never touched by any
> prior PR. A live scan (scan `#18`) confirmed fresh detection: 6 real OSV
> advisories, all `HIGH` severity, real GHSA IDs, package `lodash` only —
> `axios` is clean. The demo is currently **armed** — ready for a live
> Scan → Detect → Decide → Patch → Verify → Deliver run on a genuinely new
> issue. Re-run the steps below (with a *different* package each time, per
> the lesson above) if the demo has since been used and the issue fixed/merged.

Developer-only. Not exposed anywhere in the TALOS UI or API — TALOS itself
has no generic "reset a repository" feature, deliberately (see Phase 8/9
known limitations). This is a manual procedure you run against your own demo
repository before a live demo or recording.

**Demo repository:** `safwanshk11/talos-demo-vulnerable-app`

As of this writing it has real history already: 3 delivered pull requests
(`#1`, `#2`, `#3`, all merged), fixing `axios` (0.21.1 → latest) and
`express` (4.17.1 → latest). Once those are merged and current, a fresh
TALOS scan finds 0 open issues on those two packages — that's real, honest
evidence of completed work, but it means a live "Scan → Detect" moment needs
a *different* dependency to introduce, not a repeat of `axios`/`express`
(a repeated package makes a live demo look like a rerun of old work).

## To re-arm the demo for a live detection

1. **Introduce a known-vulnerable, known-fixable dependency TALOS hasn't
   already fixed on this repo** — pick a package with a real, well-documented
   CVE/GHSA advisory and a safe `latest` target. Already used once, working:
   `lodash@4.17.15` (prototype pollution, 6 real GHSA advisories, fixed by
   `latest`). Other good candidates for *next* time, so each demo run is
   genuinely new and not a repeat of the last one: `minimist@1.2.5`
   (prototype pollution), `y18n@4.0.0`, `node-fetch@2.6.0`. Avoid reusing
   `axios`, `express`, or `lodash` once they've already been the subject of
   a merged PR — pick whichever of the above hasn't been used yet.
   ```bash
   git clone https://github.com/safwanshk11/talos-demo-vulnerable-app.git
   cd talos-demo-vulnerable-app
   npm install <package>@<known-vulnerable-version> --save-exact --package-lock-only --no-audit --no-fund
   git add package.json package-lock.json
   git commit -m "chore: introduce <package>@<version> for a fresh TALOS demo"
   git push origin main
   ```

2. **Remove stale TALOS branches**, if any `talos/fix-*` branches remain from
   prior runs and would confuse a fresh detection:
   ```bash
   git branch -r | grep 'origin/talos/fix-' | sed 's#origin/##' | xargs -I{} git push origin --delete {}
   ```

3. **Close any stale demo PR** left open from a prior test run (the 3
   existing PRs are already merged and don't need touching — only close one
   if you created an extra unmerged test PR since).

4. **Do not reset TALOS's own database records.** The 29-job history on this
   repository is real, valuable evidence (including honest `verification_failed`
   attempts) — deleting it to make the demo "look cleaner" would remove the
   most convincing part of the story. Leave it. A fresh scan naturally creates
   a new issue/job on top of the existing history; it doesn't need a clean slate.

5. **Confirm detection works**: from the TALOS UI, open the repository and
   click **Scan Repository**, or run:
   ```bash
   ./scripts/demo-preflight.sh safwanshk11/talos-demo-vulnerable-app
   ```
   and check the "open issue(s)" line reports a nonzero count after the scan.

## What NOT to do

- Don't force-push over `main`'s history — rewriting history on a repo with
  merged PRs referencing specific commits is unnecessary and risks breaking
  the PR links already shown as evidence.
- Don't delete the merged PRs — they're real proof TALOS's output was good
  enough for a human to actually merge. That's stronger evidence than a live
  demo alone.
- Don't build this into TALOS itself as a UI feature. A "reset repository"
  button in the product would be a genuinely dangerous, easily-misclicked
  capability for a system that already does real git operations — it stays a
  manual, developer-only script forever, not a roadmap item.

#!/usr/bin/env bash
# TALOS Demo Preflight — run this before any live demo/recording.
#
# Checks the things that would actually embarrass you mid-demo. Never prints
# secrets. Exits non-zero if anything critical is broken.
#
# Usage:
#   ./scripts/demo-preflight.sh [demo-repo-full-name]
#
# demo-repo-full-name defaults to safwanshk11/talos-demo-vulnerable-app.

set -uo pipefail
cd "$(dirname "$0")/.."

DEMO_REPO="${1:-safwanshk11/talos-demo-vulnerable-app}"
FRONTEND_URL="${TALOS_FRONTEND_URL:-http://localhost:3000}"
BACKEND_URL="${TALOS_BACKEND_URL:-http://localhost:8000}"

PASS=0
FAIL=0

ok()   { printf "  \033[32m✔\033[0m %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  \033[31m✘\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }
info() { printf "  \033[2m·\033[0m %s\n" "$1"; }

echo ""
echo "TALOS DEMO PREFLIGHT"
echo ""

# 1. Frontend reachable
if curl -sf -o /dev/null --max-time 5 "$FRONTEND_URL/"; then
  ok "Frontend reachable ($FRONTEND_URL)"
else
  bad "Frontend NOT reachable ($FRONTEND_URL) — is 'docker compose up' running?"
fi

# 2. Backend + database reachable
HEALTH_JSON="$(curl -sf --max-time 5 "$BACKEND_URL/api/v1/health" 2>/dev/null)"
if [ -n "$HEALTH_JSON" ]; then
  ok "Backend API reachable ($BACKEND_URL)"
  DB_STATUS="$(echo "$HEALTH_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("database","unknown"))' 2>/dev/null)"
  if [ "$DB_STATUS" = "healthy" ]; then
    ok "Database healthy"
  else
    bad "Database NOT healthy: $DB_STATUS"
  fi
  AI_PROVIDER="$(echo "$HEALTH_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("ai_provider","unknown"))' 2>/dev/null)"
  AI_MODEL="$(echo "$HEALTH_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("ai_model","unknown"))' 2>/dev/null)"
  info "AI provider configured: $AI_PROVIDER ($AI_MODEL)"
else
  bad "Backend API NOT reachable ($BACKEND_URL) — is 'docker compose up' running?"
  AI_PROVIDER=""
fi

# 3. AI provider actually reachable (not just configured)
if [ "$AI_PROVIDER" = "ollama" ]; then
  OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
  if curl -sf -o /dev/null --max-time 5 "$OLLAMA_URL/api/tags"; then
    ok "Ollama reachable ($OLLAMA_URL)"
  else
    bad "Ollama NOT reachable ($OLLAMA_URL) — patch generation will fail. Start Ollama or switch AI_PROVIDER=gemini."
  fi
elif [ "$AI_PROVIDER" = "gemini" ]; then
  if [ -n "${GEMINI_API_KEY:-}" ]; then
    ok "Gemini API key present in this shell's environment"
  else
    info "GEMINI_API_KEY not present in this shell — checked at container startup instead, not verifiable from here."
  fi
elif [ -n "$AI_PROVIDER" ]; then
  bad "Unrecognized AI_PROVIDER: $AI_PROVIDER"
fi

# 4. Docker available (verification sandbox depends on this)
if docker info >/dev/null 2>&1; then
  ok "Docker daemon available (required for the Phase 4 verification sandbox)"
else
  bad "Docker daemon NOT available — verification will fail for every job."
fi

# 5. TALOS containers healthy
if command -v docker >/dev/null 2>&1 && docker compose ps >/dev/null 2>&1; then
  UNHEALTHY="$(docker compose ps --format '{{.Name}} {{.Status}}' 2>/dev/null | grep -v 'healthy' | grep -v '^$' || true)"
  if [ -z "$UNHEALTHY" ]; then
    ok "All docker compose services report healthy"
  else
    bad "Some services are not healthy:"
    echo "$UNHEALTHY" | sed 's/^/      /'
  fi
fi

# 6. GitHub credentials configured (never print the value)
if [ -f .env ] && grep -q '^GITHUB_PERSONAL_ACCESS_TOKEN=.\+' .env 2>/dev/null; then
  ok "GitHub Personal Access Token configured in .env"
elif [ -f .env ] && grep -q '^GITHUB_CLIENT_ID=.\+' .env 2>/dev/null; then
  ok "GitHub OAuth App configured in .env"
else
  bad "No GitHub credentials found in .env (GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_CLIENT_ID) — login will fail."
fi

# 7. Demo repository connected and reachable (reads the DB directly — no auth token needed)
REPO_ROW="$(docker compose exec -T postgres psql -U talos -d talos_db -t -A -c \
  "SELECT connection_status || '|' || monitoring_status || '|' || COALESCE(last_scanned_at::text,'never') FROM repositories WHERE full_name = '$DEMO_REPO';" 2>/dev/null | tr -d '\r')"
if [ -n "$REPO_ROW" ]; then
  CONN_STATUS="$(echo "$REPO_ROW" | cut -d'|' -f1)"
  MON_STATUS="$(echo "$REPO_ROW" | cut -d'|' -f2)"
  LAST_SCAN="$(echo "$REPO_ROW" | cut -d'|' -f3)"
  if [ "$CONN_STATUS" = "connected" ] || [ "$CONN_STATUS" != "disconnected" ]; then
    ok "Demo repository connected: $DEMO_REPO (monitoring: $MON_STATUS, last scan: $LAST_SCAN)"
  else
    bad "Demo repository $DEMO_REPO is disconnected — reconnect it before the demo."
  fi
else
  bad "Demo repository $DEMO_REPO not found in TALOS — connect it before the demo, or pass the correct full_name as an argument."
fi

# 8. Open issues on the demo repo (what the live demo will actually show)
OPEN_ISSUES="$(docker compose exec -T postgres psql -U talos -d talos_db -t -A -c \
  "SELECT count(*) FROM maintenance_issues mi JOIN repositories r ON r.id = mi.repository_id WHERE r.full_name = '$DEMO_REPO' AND mi.status = 'OPEN';" 2>/dev/null | tr -d '\r')"
if [ "${OPEN_ISSUES:-0}" -gt 0 ] 2>/dev/null; then
  ok "$OPEN_ISSUES open issue(s) on the demo repository — a live 'Scan → Detect' run has something to find."
else
  info "0 open issues on the demo repository right now — a fresh scan will find nothing new. Run scripts/demo-reset.md's steps first if you need a live detection moment, or use existing delivered PR history as evidence instead."
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo -e "\033[32mREADY\033[0m  ($PASS checks passed)"
  exit 0
else
  echo -e "\033[31mNOT READY\033[0m  ($FAIL failed, $PASS passed) — fix the ✘ items above before demoing."
  exit 1
fi

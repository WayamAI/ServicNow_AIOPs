#!/usr/bin/env bash
# scripts/demo_stopped_container.sh
#
# End-to-end demo for ServiceNow AIOPs.
# Creates a stopped nginx container, submits an incident, watches the
# RCA → Plan → Execution → Validation pipeline, and prints a formatted report.
#
# Usage:  bash scripts/demo_stopped_container.sh
# Re-run: idempotent — cleans up old container; only stops server if this script started it.
#
set -euo pipefail

# ── ANSI colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL="http://localhost:8000"
CONTAINER_NAME="demo-aiops-nginx"
POLL_INTERVAL=3
POLL_TIMEOUT=300        # 5 minutes
SERVER_START_TIMEOUT=30 # seconds to wait for uvicorn

# ── Script-level state ────────────────────────────────────────────────────────
SERVER_PID=""
SSE_PID=""
WE_STARTED_SERVER=false

# ── Helpers ───────────────────────────────────────────────────────────────────
info()   { printf "${CYAN}[INFO]${RESET}  %s\n" "$*"; }
ok()     { printf "${GREEN}[OK]${RESET}    %s\n" "$*"; }
warn()   { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
err()    { printf "${RED}[ERR]${RESET}   %s\n" "$*" >&2; }
header() { printf "\n${BOLD}${BLUE}══ %s ══${RESET}\n" "$*"; }

# ── Cleanup trap ──────────────────────────────────────────────────────────────
_cleanup() {
    if [[ -n "$SSE_PID" ]] && kill -0 "$SSE_PID" 2>/dev/null; then
        kill "$SSE_PID" 2>/dev/null || true
    fi
    if [[ "$WE_STARTED_SERVER" == true && -n "$SERVER_PID" ]]; then
        info "Stopping background server (PID ${SERVER_PID})..."
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}
trap _cleanup EXIT INT TERM

# ─────────────────────────────────────────────────────────────────────────────
# Section 1: Prerequisite checks
# ─────────────────────────────────────────────────────────────────────────────
header "Checking prerequisites"

MISSING=()
for cmd in docker curl jq; do
    command -v "$cmd" &>/dev/null || MISSING+=("$cmd")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    err "Missing required tools: ${MISSING[*]}"
    err "Install them and re-run."
    exit 1
fi
ok "docker, curl, jq — all present"

# ─────────────────────────────────────────────────────────────────────────────
# Section 2: Backend API liveness check + conditional startup
# ─────────────────────────────────────────────────────────────────────────────
header "Checking backend API"

_api_is_up() {
    curl -sf "${BASE_URL}/health" &>/dev/null
}

if _api_is_up; then
    ok "Backend already running on port 8000"
else
    info "Backend not running — starting uvicorn in background..."

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    SERVER_LOG="/tmp/aiops_demo_server_$$.log"

    (cd "$PROJECT_ROOT" && uv run uvicorn main:app --host 0.0.0.0 --port 8000) \
        >"$SERVER_LOG" 2>&1 &
    SERVER_PID=$!
    WE_STARTED_SERVER=true

    DEADLINE=$(( $(date +%s) + SERVER_START_TIMEOUT ))
    info "Waiting up to ${SERVER_START_TIMEOUT}s for server to become ready..."
    while true; do
        if _api_is_up; then
            ok "Server is ready (PID ${SERVER_PID})"
            break
        fi
        if [[ $(date +%s) -ge $DEADLINE ]]; then
            err "Server did not become ready in ${SERVER_START_TIMEOUT}s"
            err "Check log: ${SERVER_LOG}"
            exit 1
        fi
        sleep 1
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# Section 3: Docker container setup (idempotent)
# ─────────────────────────────────────────────────────────────────────────────
header "Setting up demo container"

if docker inspect "$CONTAINER_NAME" &>/dev/null; then
    info "Removing existing container '${CONTAINER_NAME}'..."
    docker rm -f "$CONTAINER_NAME" &>/dev/null
fi

info "Creating nginx container '${CONTAINER_NAME}'..."
docker run -d --name "$CONTAINER_NAME" nginx:latest &>/dev/null
docker stop "$CONTAINER_NAME" &>/dev/null
ok "Container '${CONTAINER_NAME}' is now STOPPED"

# ─────────────────────────────────────────────────────────────────────────────
# Section 4: Before state
# ─────────────────────────────────────────────────────────────────────────────
header "Before state"
printf "${DIM}"
docker ps -a --filter "name=${CONTAINER_NAME}" \
    --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
printf "${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# Section 5: Create session
# ─────────────────────────────────────────────────────────────────────────────
header "Creating AIOps session"

SESSION_JSON=$(curl -sf -X POST "${BASE_URL}/sessions" \
    -H "Content-Type: application/json" \
    -d '{}')
SESSION_ID=$(printf '%s' "$SESSION_JSON" | jq -r '.id')
ok "Session created: ${SESSION_ID}"

# ─────────────────────────────────────────────────────────────────────────────
# Section 6: SSE listener in background
# ─────────────────────────────────────────────────────────────────────────────
header "Starting live event stream"

_sse_listener() {
    local sid="$1"
    curl -sN "${BASE_URL}/sessions/${sid}/stream" | while IFS= read -r line; do
        [[ "$line" == data:* ]] || continue
        local payload="${line#data: }"
        [[ -z "$payload" || "$payload" == "{}" ]] && continue

        local event_type agent_name
        event_type=$(printf '%s' "$payload" | jq -r '.event_type // empty' 2>/dev/null) || continue
        agent_name=$(printf '%s'  "$payload" | jq -r '.agent_name  // empty' 2>/dev/null) || true

        case "$event_type" in
            agent_start)
                printf "${YELLOW}  [LIVE] Agent started: ${BOLD}%s${RESET}\n" "$agent_name"
                ;;
            tool_call)
                local tool_name
                tool_name=$(printf '%s' "$payload" \
                    | jq -r '.payload.tool_name // .payload.name // "tool"' 2>/dev/null) || true
                printf "${DIM}  [LIVE] %-20s → %s${RESET}\n" "$agent_name" "$tool_name"
                ;;
            agent_response)
                printf "${CYAN}  [LIVE] Agent response: ${BOLD}%s${RESET}\n" "$agent_name"
                ;;
            error)
                local msg
                msg=$(printf '%s' "$payload" \
                    | jq -r '.payload.message // "unknown error"' 2>/dev/null) || true
                printf "${RED}  [LIVE] Error: %s${RESET}\n" "$msg"
                ;;
        esac
    done
}

_sse_listener "$SESSION_ID" &
SSE_PID=$!
ok "SSE listener started (PID ${SSE_PID})"

# ─────────────────────────────────────────────────────────────────────────────
# Section 7: Create incident
# ─────────────────────────────────────────────────────────────────────────────
header "Creating incident"

INCIDENT_JSON=$(curl -sf -X POST \
    "${BASE_URL}/sessions/${SESSION_ID}/incidents" \
    -H "Content-Type: application/json" \
    -d "{
        \"title\":          \"nginx container stopped\",
        \"description\":    \"Container ${CONTAINER_NAME} is not running. It needs to be started.\",
        \"container_name\": \"${CONTAINER_NAME}\",
        \"severity\":       \"high\"
    }")

INCIDENT_ID=$(printf '%s' "$INCIDENT_JSON" | jq -r '.id')
INCIDENT_STATUS=$(printf '%s' "$INCIDENT_JSON" | jq -r '.status')
ok "Incident created: ${INCIDENT_ID} (initial status: ${INCIDENT_STATUS})"

# ─────────────────────────────────────────────────────────────────────────────
# Section 8: Poll until terminal state
# ─────────────────────────────────────────────────────────────────────────────
header "Waiting for pipeline to complete"
info "Polling every ${POLL_INTERVAL}s (timeout: ${POLL_TIMEOUT}s)..."

DEADLINE=$(( $(date +%s) + POLL_TIMEOUT ))
LAST_STATUS=""
FINAL_STATUS=""

while true; do
    if [[ $(date +%s) -ge $DEADLINE ]]; then
        err "Timed out after ${POLL_TIMEOUT}s waiting for resolution"
        exit 1
    fi

    POLL_JSON=$(curl -sf "${BASE_URL}/incidents/${INCIDENT_ID}") || {
        warn "Poll request failed, retrying..."
        sleep "$POLL_INTERVAL"
        continue
    }

    STATUS=$(printf '%s' "$POLL_JSON" | jq -r '.status')

    if [[ "$STATUS" != "$LAST_STATUS" ]]; then
        case "$STATUS" in
            resolved)          printf "  ${GREEN}● Status: %s${RESET}\n" "$STATUS" ;;
            failed|cancelled)  printf "  ${RED}● Status: %s${RESET}\n"   "$STATUS" ;;
            *)                 printf "  ${YELLOW}● Status: %s${RESET}\n" "$STATUS" ;;
        esac
        LAST_STATUS="$STATUS"
    fi

    case "$STATUS" in
        resolved|failed|cancelled)
            FINAL_STATUS="$STATUS"
            break
            ;;
    esac

    sleep "$POLL_INTERVAL"
done

ok "Pipeline finished: ${FINAL_STATUS}"

# ─────────────────────────────────────────────────────────────────────────────
# Section 9: Stop SSE listener
# ─────────────────────────────────────────────────────────────────────────────
if [[ -n "$SSE_PID" ]] && kill -0 "$SSE_PID" 2>/dev/null; then
    kill "$SSE_PID" 2>/dev/null || true
    SSE_PID=""
fi
sleep 1  # let any buffered output flush

# ─────────────────────────────────────────────────────────────────────────────
# Section 10: Fetch and render report
# ─────────────────────────────────────────────────────────────────────────────
header "Fetching incident report"

REPORT_JSON=$(curl -sf "${BASE_URL}/incidents/${INCIDENT_ID}/report")
INC_BLOCK=$(printf '%s'  "$REPORT_JSON" | jq '.json.incident')
LATEST_RUN=$(printf '%s' "$REPORT_JSON" | jq '.json.runs[-1]')

# ── Report header ─────────────────────────────────────────────────────────────
printf "\n${BOLD}${BLUE}"
printf '╔══════════════════════════════════════════════╗\n'
printf '║            INCIDENT REPORT                   ║\n'
printf '╚══════════════════════════════════════════════╝\n'
printf "${RESET}\n"

TITLE=$(    printf '%s' "$INC_BLOCK" | jq -r '.title')
SEVERITY=$( printf '%s' "$INC_BLOCK" | jq -r '.severity')
DURATION=$( printf '%s' "$INC_BLOCK" | jq -r '.duration')
INC_STATUS=$(printf '%s' "$INC_BLOCK" | jq -r '.status')

printf "${BOLD}Title:${RESET}    %s\n" "$TITLE"
printf "${BOLD}Status:${RESET}   %s\n" "$INC_STATUS"
printf "${BOLD}Severity:${RESET} %s\n" "$SEVERITY"
printf "${BOLD}Duration:${RESET} %s\n" "$DURATION"

# ── RCA ───────────────────────────────────────────────────────────────────────
printf "\n${BOLD}${GREEN}── Root Cause Analysis ──${RESET}\n"
RCA=$(printf '%s' "$LATEST_RUN" | jq '.rca_result')
if [[ "$RCA" != "null" && -n "$RCA" ]]; then
    ROOT_CAUSE=$(  printf '%s' "$RCA" | jq -r '.root_cause // "unknown"')
    CATEGORY=$(    printf '%s' "$RCA" | jq -r '.category   // "unknown"')
    CONFIDENCE=$(  printf '%s' "$RCA" | jq -r '.confidence // 0')
    DETAILS=$(     printf '%s' "$RCA" | jq -r '.details    // ""')
    CONF_PCT=$(awk "BEGIN{printf \"%.0f\", ${CONFIDENCE}*100}")

    printf "  ${GREEN}Root Cause:${RESET}  %s\n"  "$ROOT_CAUSE"
    printf "  ${GREEN}Category:${RESET}    %s\n"  "$CATEGORY"
    printf "  ${GREEN}Confidence:${RESET}  %s%%\n" "$CONF_PCT"
    [[ -n "$DETAILS" ]] && printf "  ${GREEN}Details:${RESET}     %s\n" "$DETAILS"

    EVIDENCE_COUNT=$(printf '%s' "$RCA" | jq '.evidence | length // 0')
    if [[ "$EVIDENCE_COUNT" -gt 0 ]]; then
        printf "  ${GREEN}Evidence:${RESET}\n"
        printf '%s' "$RCA" | jq -r '.evidence[]' | while IFS= read -r item; do
            printf "    • %s\n" "$item"
        done
    fi
else
    printf "  (no RCA data)\n"
fi

# ── Plan ──────────────────────────────────────────────────────────────────────
printf "\n${BOLD}${CYAN}── Remediation Plan ──${RESET}\n"
PLAN=$(printf '%s' "$LATEST_RUN" | jq '.plan_result')
if [[ "$PLAN" != "null" && -n "$PLAN" ]]; then
    STRATEGY=$(printf '%s' "$PLAN" | jq -r '.overall_strategy // ""')
    RISK=$(     printf '%s' "$PLAN" | jq -r '.estimated_risk   // "unknown"')

    printf "  ${CYAN}Strategy:${RESET} %s\n" "$STRATEGY"
    printf "  ${CYAN}Risk:${RESET}     %s\n" "$RISK"
    printf "  ${CYAN}Steps:${RESET}\n"
    printf '%s' "$PLAN" | jq -r '.steps[] | "    \(.step_number). \(.action)"' \
        | while IFS= read -r step_line; do
            printf "%s\n" "$step_line"
        done
else
    printf "  (no plan data)\n"
fi

# ── Execution ─────────────────────────────────────────────────────────────────
printf "\n${BOLD}${YELLOW}── Execution ──${RESET}\n"
EXEC=$(printf '%s' "$LATEST_RUN" | jq '.execution_result')
if [[ "$EXEC" != "null" && -n "$EXEC" ]]; then
    OVERALL=$(     printf '%s' "$EXEC" | jq -r '.overall_success      // false')
    CTR_AFTER=$(   printf '%s' "$EXEC" | jq -r '.container_status_after // "unknown"')
    SUCCESS_COLOR=$([[ "$OVERALL" == "true" ]] && printf '%s' "$GREEN" || printf '%s' "$RED")

    printf "  ${YELLOW}Overall Success:${RESET}  ${SUCCESS_COLOR}%s${RESET}\n" "$OVERALL"
    printf "  ${YELLOW}Container After:${RESET}  %s\n" "$CTR_AFTER"

    STEP_COUNT=$(printf '%s' "$EXEC" | jq '.executed_steps | length // 0')
    if [[ "$STEP_COUNT" -gt 0 ]]; then
        printf "  ${YELLOW}Steps Taken:${RESET}\n"
        printf '%s' "$EXEC" | jq -r \
            '.executed_steps[] | "    \(.step_number). [\(.tool_used // "?")] \(.action_taken) → \(if .success then "✓" else "✗" end)"' \
            | while IFS= read -r exec_line; do
                printf "%s\n" "$exec_line"
            done
    fi
else
    printf "  (no execution data)\n"
fi

# ── Validation ────────────────────────────────────────────────────────────────
printf "\n${BOLD}── Validation ──${RESET}\n"
VAL=$(printf '%s' "$LATEST_RUN" | jq '.validation_result')
if [[ "$VAL" != "null" && -n "$VAL" ]]; then
    VALIDATED=$(  printf '%s' "$VAL" | jq -r '.validated  // false')
    VAL_CONF=$(   printf '%s' "$VAL" | jq -r '.confidence // 0')
    CTR_STATUS=$( printf '%s' "$VAL" | jq -r '.container_status // "unknown"')
    VAL_CONF_PCT=$(awk "BEGIN{printf \"%.0f\", ${VAL_CONF}*100}")

    if [[ "$VALIDATED" == "true" ]]; then
        printf "  ${GREEN}✓  Validated: YES${RESET}\n"
    else
        printf "  ${RED}✗  Validated: NO${RESET}\n"
    fi
    printf "  Container Status: %s\n" "$CTR_STATUS"
    printf "  Confidence:       %s%%\n" "$VAL_CONF_PCT"

    CHECK_COUNT=$(printf '%s' "$VAL" | jq '.checks | length // 0')
    if [[ "$CHECK_COUNT" -gt 0 ]]; then
        printf "  Checks:\n"
        printf '%s' "$VAL" | jq -r \
            '.checks[] | "    \(if .passed then "✓" else "✗" end) \(.check): \(.result)"' \
            | while IFS= read -r check_line; do
                printf "%s\n" "$check_line"
            done
    fi
else
    printf "  (no validation data)\n"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Section 11: After state + final outcome
# ─────────────────────────────────────────────────────────────────────────────
header "After state"
printf "${DIM}"
docker ps -a --filter "name=${CONTAINER_NAME}" \
    --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
printf "${RESET}\n"

printf "\n"
if [[ "$FINAL_STATUS" == "resolved" ]]; then
    printf "${BOLD}${GREEN}Demo complete — incident RESOLVED successfully.${RESET}\n\n"
else
    printf "${BOLD}${RED}Demo complete — incident ended with status: ${FINAL_STATUS}${RESET}\n\n"
fi

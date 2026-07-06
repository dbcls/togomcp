#!/usr/bin/env bash
#
# deploy.sh — safe test-before-prod deployment for the togomcp Podman host (vs94).
#
#   ./deploy.sh test        Build a candidate image, (re)create the TEST container, smoke-test it.
#   ./deploy.sh prod        Promote the *exact image currently on TEST* to PRODUCTION.
#                           Requires: TEST is green AND operator types the prod hostname.
#   ./deploy.sh rollback    Restore PRODUCTION to the image it ran before the last promote.
#   ./deploy.sh status      Show what each container is currently running.
#
# Guarantees that prevent the "accidentally updated prod first" class of mistake:
#   * prod NEVER builds — it can only promote bytes that were already deployed & tested on test.
#   * `prod` refuses to run unless the test container exists and answers 200 right now.
#   * `prod` requires the operator to type the production hostname; any mismatch aborts
#     with zero changes.
#   * every promote saves a rollback pointer.
#
# Env values are loaded from the first source that exists:
#   1. $TOGOMCP_ENV_FILE   (explicit override path)
#   2. <repo>/.env         (the same file compose reads)
#   3. the current shell
# Per-service vars take their _TEST variant on the test container, matching
# compose.yaml (TOGOMCP_STATS_PASSWORD_TEST -> test, TOGOMCP_STATS_PASSWORD -> prod).
#
set -euo pipefail

# --------------------------------------------------------------------------- #
# Config — EDIT if container names / ports / public hostnames change.
# --------------------------------------------------------------------------- #
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_REPO="localhost/togo-mcp"

TEST_CONTAINER="togomcp-test"
TEST_TAG="dev"
TEST_PORT=8001
TEST_SMOKE_HOST="test-togomcp.rdfportal.org"   # Host header used for the test smoke check

PROD_CONTAINER="togomcp-main"
PROD_TAG="latest"
PROD_PORT=8000
PROD_SMOKE_HOST="togomcp.rdfportal.org"         # Host header used for the prod smoke check

# The operator must type this EXACT string to confirm a production deploy.
# Set it to your real public production hostname.
PROD_CONFIRM_PHRASE="togomcp.rdfportal.org"

# Vars forwarded to each container. Per-service vars take their _TEST variant on
# the test container (mirrors compose.yaml); shared vars are identical for both.
TOGOMCP_PERSERVICE_VARS=(TOGOMCP_ALLOWED_HOSTS TOGOMCP_QUERY_LOG TOGOMCP_LOG_QUERY_TEXT \
                         TOGOMCP_STATS_USER TOGOMCP_STATS_PASSWORD TOGOMCP_LOG_HASH_SALT)
TOGOMCP_SHARED_VARS=(NCBI_API_KEY)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[deploy:warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[deploy:error]\033[0m %s\n' "$*" >&2; exit 1; }

load_dotenv() {  # file — safe KEY=VALUE parse, no code execution
  local file=$1 line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"                       # strip trailing CR
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue   # comment / blank
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"; val="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ -z "$key" ]] && continue
    if [[ "$val" == \"*\" || "$val" == \'*\' ]]; then val="${val:1:${#val}-2}"; fi
    export "$key=$val"
  done < "$file"
}

_resolve() {  # kind(test|prod) var  -> prints the effective value
  local name="$2"
  [[ "$1" == test ]] && name="${2}_TEST"
  printf '%s' "${!name:-}"
}

env_args() {  # kind(test|prod) — prints podman -e args, one token per line
  local kind=$1 v val any=0
  for v in "${TOGOMCP_PERSERVICE_VARS[@]}"; do
    val=$(_resolve "$kind" "$v")
    printf -- '-e\n%s=%s\n' "$v" "$val"; [[ -n "$val" ]] && any=1
  done
  for v in "${TOGOMCP_SHARED_VARS[@]}"; do
    val="${!v:-}"
    printf -- '-e\n%s=%s\n' "$v" "$val"; [[ -n "$val" ]] && any=1
  done
  [[ "$any" == 1 ]] || warn "no env values found (checked ${ENV_SOURCE:-current shell}); container starts with empty config."
}

recreate() {  # name port image kind
  local name=$1 port=$2 image=$3 kind=$4 eargs=()
  mapfile -t eargs < <(env_args "$kind")
  # Bind-mount the log dir like compose does (main -> ./logs, test -> ./logs-test),
  # so a TOGOMCP_QUERY_LOG path under /var/log/togomcp exists and persists.
  local logdir="$REPO_ROOT/logs"; [[ "$kind" == test ]] && logdir="$REPO_ROOT/logs-test"
  mkdir -p "$logdir"
  log "recreating '$name' on :$port from ${image}"
  podman rm -f "$name" >/dev/null 2>&1 || true
  podman run -d --name "$name" -p "${port}:8000" -v "${logdir}:/var/log/togomcp" \
    "${eargs[@]}" "$image" >/dev/null
}

smoke() {  # port host label  -> dies unless 200
  local port=$1 host=$2 label=$3 code=""
  for _ in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $host" "http://127.0.0.1:${port}/" 2>/dev/null || true)
    [[ "$code" == "200" ]] && { log "smoke OK: $label :$port Host=$host -> 200"; return 0; }
    sleep 1
  done
  die "smoke FAILED: $label :$port Host=$host -> ${code:-no-response} (expected 200)"
}

img_id()   { podman image inspect "$1" --format '{{.Id}}' 2>/dev/null; }
short()    { printf '%.19s' "$1"; }

# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
cmd_test() {
  local commit; commit=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo '?')
  log "building candidate from $REPO_ROOT (commit $commit)"
  local build_args=(); [[ "${NO_CACHE:-0}" == "1" ]] && build_args+=(--no-cache)
  podman build "${build_args[@]}" -t "${IMAGE_REPO}:${TEST_TAG}" "$REPO_ROOT"
  log "built ${IMAGE_REPO}:${TEST_TAG} = $(short "$(img_id "${IMAGE_REPO}:${TEST_TAG}")")"
  recreate "$TEST_CONTAINER" "$TEST_PORT" "${IMAGE_REPO}:${TEST_TAG}" test
  smoke "$TEST_PORT" "$TEST_SMOKE_HOST" "TEST"
  log "TEST is up and healthy. Review it, then promote with:  $0 prod"
}

cmd_prod() {
  # 1. Enforce test-before-prod: there must be a running test container to promote from.
  podman container exists "$TEST_CONTAINER" \
    || die "no '$TEST_CONTAINER' running — run '$0 test' first (test-before-prod is enforced)"
  local candidate; candidate=$(podman inspect "$TEST_CONTAINER" --format '{{.Image}}') \
    || die "cannot read image of $TEST_CONTAINER"
  log "promotion candidate = image $(short "$candidate") (currently running on $TEST_CONTAINER)"

  # 2. Gate: test must be green right now.
  log "verifying TEST is healthy before allowing promotion..."
  smoke "$TEST_PORT" "$TEST_SMOKE_HOST" "TEST(gate)"

  # 3. Human confirmation: type the production hostname.
  printf '\n\033[1;41m *** PRODUCTION DEPLOY *** \033[0m  container=%s  port=%s\n' \
    "$PROD_CONTAINER" "$PROD_PORT"
  printf 'This promotes the TESTED image above to PRODUCTION.\n'
  printf 'Type the production hostname to confirm (anything else aborts):\n> '
  local reply=""; read -r reply || true
  [[ "$reply" == "$PROD_CONFIRM_PHRASE" ]] \
    || die "confirmation mismatch — aborted, nothing changed."

  # 4. Save a rollback pointer to the outgoing prod image.
  if podman container exists "$PROD_CONTAINER"; then
    local prev; prev=$(podman inspect "$PROD_CONTAINER" --format '{{.Image}}')
    podman tag "$prev" "${IMAGE_REPO}:prod-previous" || true
    log "saved rollback image $(short "$prev") as ${IMAGE_REPO}:prod-previous"
  fi

  # 5. Promote the SAME bytes that were tested (no rebuild), then recreate prod.
  podman tag "$candidate" "${IMAGE_REPO}:${PROD_TAG}"
  recreate "$PROD_CONTAINER" "$PROD_PORT" "${IMAGE_REPO}:${PROD_TAG}" prod

  # 6. Smoke-test production.
  smoke "$PROD_PORT" "$PROD_SMOKE_HOST" "PROD"
  log "PRODUCTION deploy complete. Rollback if needed with:  $0 rollback"
}

cmd_rollback() {
  podman image exists "${IMAGE_REPO}:prod-previous" \
    || die "no ${IMAGE_REPO}:prod-previous saved — nothing to roll back to"
  log "rolling PRODUCTION back to ${IMAGE_REPO}:prod-previous ($(short "$(img_id "${IMAGE_REPO}:prod-previous")"))"
  podman tag "${IMAGE_REPO}:prod-previous" "${IMAGE_REPO}:${PROD_TAG}"
  recreate "$PROD_CONTAINER" "$PROD_PORT" "${IMAGE_REPO}:${PROD_TAG}" prod
  smoke "$PROD_PORT" "$PROD_SMOKE_HOST" "PROD(rollback)"
  log "rollback complete."
}

cmd_status() {
  local c img
  for c in "$TEST_CONTAINER" "$PROD_CONTAINER"; do
    if podman container exists "$c"; then
      img=$(podman inspect "$c" --format '{{.ImageName}} ({{slice .Image 0 19}})')
      printf '%-16s %s  %s\n' "$c" "$(podman inspect "$c" --format '{{.State.Status}}')" "$img"
    else
      printf '%-16s (not present)\n' "$c"
    fi
  done
}

# --------------------------------------------------------------------------- #
# Load env source: explicit override > repo .env > current shell
# --------------------------------------------------------------------------- #
ENV_SOURCE="${TOGOMCP_ENV_FILE:-}"
[[ -z "$ENV_SOURCE" && -f "$REPO_ROOT/.env" ]] && ENV_SOURCE="$REPO_ROOT/.env"
if [[ -n "$ENV_SOURCE" ]]; then
  [[ -f "$ENV_SOURCE" ]] || die "env file not found: $ENV_SOURCE"
  load_dotenv "$ENV_SOURCE"
  log "loaded env from $ENV_SOURCE"
fi

# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
case "${1:-}" in
  test)     cmd_test ;;
  prod)     cmd_prod ;;
  rollback) cmd_rollback ;;
  status)   cmd_status ;;
  *)
    cat >&2 <<USAGE
Usage: $0 {test|prod|rollback|status}

  test      Build candidate, (re)create TEST ($TEST_CONTAINER, :$TEST_PORT), smoke-test.
  prod      Promote the image running on TEST to PROD ($PROD_CONTAINER, :$PROD_PORT).
            Requires TEST green + typing '$PROD_CONFIRM_PHRASE'. Never rebuilds.
  rollback  Restore PROD to the previous image.
  status    Show current image per container.

Optional env:
  TOGOMCP_ENV_FILE=/path/to/env   Load this file instead of <repo>/.env.
  NO_CACHE=1                      Force a clean rebuild in 'test'.
USAGE
    exit 1 ;;
esac

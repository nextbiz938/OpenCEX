#!/usr/bin/env bash
# Non-interactive smoke-test equivalent of the frontend/nuxt/admin part of opencex.sh (~lines 675-710):
#   1. renders the three app configs from the upstream templates with the smoke-test values
#      (plain http://localhost, ws:// websockets) into ../config/ and into the app checkouts,
#   2. puts the nginx confs where the installer puts them (<checkout>/deploy/),
#   3. builds opencex-frontend:smoke, opencex-nuxt:smoke and opencex-admin:smoke in parallel.
# Builds the images only; it does not start anything.
#
# RENDER_ONLY=1 stops after step 2. Overridable via environment: FRONTEND_DIR NUXT_DIR ADMIN_DIR CA_BUNDLE LOG_DIR NUXT_API_URL MIN_FREE_GB
# and every template variable below.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SMOKE=$(dirname "$HERE")
INSTALLER=$(dirname "$SMOKE")
SRC_ROOT=$(dirname "$INSTALLER")

FRONTEND_DIR=${FRONTEND_DIR:-$SRC_ROOT/OpenCEX-frontend}
NUXT_DIR=${NUXT_DIR:-$SRC_ROOT/OpenCEX-static}
ADMIN_DIR=${ADMIN_DIR:-$SRC_ROOT/OpenCEX-JS-admin}
# Only needed behind a TLS-intercepting proxy; skipped when the file does not exist.
CA_BUNDLE=${CA_BUNDLE:-/root/.ccr/ca-bundle.crt}
LOG_DIR=${LOG_DIR:-$(mktemp -d -t opencex-frontends-build.XXXXXX)}
MIN_FREE_GB=${MIN_FREE_GB:-3}

# ---- smoke-test values (installer prompts for these) ---------------------------------------------
export PROJECT_NAME=${PROJECT_NAME:-OpenCEXSmoke}
export DOMAIN=${DOMAIN:-localhost}
export ADMIN_BASE_URL=${ADMIN_BASE_URL:-admin}
export RECAPTCHA=${RECAPTCHA:-6LeIxAcTAAAAAJcZVRqyHh4FAAAAAAAAAAAA4}   # Google's public test site key
export TELEGRAM=${TELEGRAM-opencex}
export FACEBOOK=${FACEBOOK-polygant}
export TWITTER=${TWITTER-polygant}
export LINKEDIN=${LINKEDIN-polygant}
export SUPPORT_EMAIL=${SUPPORT_EMAIL-support@localhost}
export LOGO=${LOGO-}
export TG_NEWS=${TG_NEWS-}
export HELP_WIDGET=${HELP_WIDGET-}
# Server-side (SSR) API base of the nuxt container. The installer uses https://$DOMAIN/ (hairpin through
# Caddy); with DOMAIN=localhost that would be the nuxt container itself, so go straight to the backend
# container (Django ALLOWED_HOSTS contains INSTANCE_NAME=opencex). Can also be overridden at
# `docker run -e API_URL=...` time.
NUXT_API_URL=${NUXT_API_URL:-http://opencex:8080/}

VARS='${PROJECT_NAME} ${DOMAIN} ${ADMIN_BASE_URL} ${RECAPTCHA} ${TELEGRAM} ${FACEBOOK} ${TWITTER} ${LINKEDIN} ${SUPPORT_EMAIL} ${LOGO} ${TG_NEWS} ${HELP_WIDGET}'

render() {  # render <template>  -> stdout; only the variables listed in VARS are substituted
  if command -v envsubst >/dev/null 2>&1; then
    envsubst "$VARS" < "$1"
  else  # no gettext-base on the host: use the envsubst shipped in the (pinned) nginx image
    docker run --rm -i -e PROJECT_NAME -e DOMAIN -e ADMIN_BASE_URL -e RECAPTCHA -e TELEGRAM -e FACEBOOK \
      -e TWITTER -e LINKEDIN -e SUPPORT_EMAIL -e LOGO -e TG_NEWS -e HELP_WIDGET \
      nginx:1.27-alpine envsubst "$VARS" < "$1"
  fi
}

check_disk() {
  df -h /
  local avail_kb
  avail_kb=$(df -Pk / | awk 'NR==2 {print $4}')
  if [ "$avail_kb" -lt $((MIN_FREE_GB * 1024 * 1024)) ]; then
    echo "ERROR: less than ${MIN_FREE_GB} GB free on /, stopping." >&2
    exit 1
  fi
}

mkdir -p "$SMOKE/config"

# ---- frontend: src/local_config (no extension, like the installer; vite resolves "~/local_config" to it)
render "$FRONTEND_DIR/src/example.local_config.js" \
  | sed -e "s#https://${DOMAIN}#http://${DOMAIN}#g" \
        -e 's#wss_url: "wss://"#wss_url: "ws://"#' \
  > "$SMOKE/config/frontend.local_config.js"
cp "$SMOKE/config/frontend.local_config.js" "$FRONTEND_DIR/src/local_config"
mkdir -p "$FRONTEND_DIR/deploy"
cp "$HERE/frontend-default.conf" "$FRONTEND_DIR/deploy/default.conf"
cp "$HERE/frontend-nginx.conf"   "$FRONTEND_DIR/deploy/nginx.conf"

# ---- nuxt: .env
render "$INSTALLER/nuxt/.env.template" \
  | sed -e "s#^API_URL=.*#API_URL=\"${NUXT_API_URL}\"#" \
        -e "s#https://${DOMAIN}#http://${DOMAIN}#g" \
  > "$SMOKE/config/nuxt.env"
echo >> "$SMOKE/config/nuxt.env"   # template has no trailing newline
cp "$SMOKE/config/nuxt.env" "$NUXT_DIR/.env"

# ---- admin: src/local_config.js
render "$INSTALLER/admin/.env.template" \
  | sed -e "s#https://${DOMAIN}#http://${DOMAIN}#g" \
  > "$SMOKE/config/admin.local_config.js"
cp "$SMOKE/config/admin.local_config.js" "$ADMIN_DIR/src/local_config.js"
mkdir -p "$ADMIN_DIR/deploy"
cp "$HERE/admin-default.conf" "$ADMIN_DIR/deploy/default.conf"

if [ "${RENDER_ONLY:-0}" = 1 ]; then echo "configs rendered into $SMOKE/config and the checkouts"; exit 0; fi

# ---- builds ---------------------------------------------------------------------------------------
SECRET_ARGS=()
if [ -s "$CA_BUNDLE" ]; then SECRET_ARGS=(--secret "id=ca,src=$CA_BUNDLE"); fi

check_disk
mkdir -p "$LOG_DIR"; echo "build logs: $LOG_DIR"

build() {  # build <name> <context>
  local name=$1 ctx=$2 start rc=0
  start=$(date +%s)
  DOCKER_BUILDKIT=1 docker build --progress=plain "${SECRET_ARGS[@]}" \
    -f "$HERE/$name.Dockerfile" -t "opencex-$name:smoke" "$ctx" > "$LOG_DIR/$name.log" 2>&1 || rc=$?
  echo "$name: exit=$rc duration=$(( $(date +%s) - start ))s log=$LOG_DIR/$name.log"
  return $rc
}

build nuxt "$NUXT_DIR" & pid_nuxt=$!
build frontend "$FRONTEND_DIR" & pid_frontend=$!
build admin "$ADMIN_DIR" & pid_admin=$!

fail=0
for pid in $pid_nuxt $pid_frontend $pid_admin; do
  wait "$pid" || fail=1
  check_disk
done

docker image ls --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' | grep -E '^opencex-(frontend|nuxt|admin):smoke' || true
exit $fail

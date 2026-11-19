#!/usr/bin/env bash
# One command to get the OpenCEX smoke-test stack running on any Linux box with Docker
# (Ubuntu VPS, a Linux PC, or Windows via WSL2 + Docker Desktop).
#
#   ./setup.sh            # clone pinned upstream repos, patch, configure, build, start, init, test
#   SKIP_SMOKE_TEST=1 ./setup.sh
#
# Safe to re-run: existing clones, .env and users are kept.
# Test values only: no real keys, no blockchains, e-mail goes to a local Mailpit.
set -euo pipefail

SMOKE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../OpenCEX/smoke-test
ROOT="$(cd "$SMOKE/../.." && pwd)"                      # upstream repos are cloned next to OpenCEX/
SECRETS="$SMOKE/secrets"
say() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 0. prerequisites
for c in docker git python3 curl; do command -v "$c" >/dev/null || die "'$c' is not installed"; done
docker compose version >/dev/null 2>&1 || die "'docker compose' (v2) is not available"
docker info >/dev/null 2>&1 || die "Docker is not running (on Windows: start Docker Desktop and enable WSL integration)"
free_gb=$(df -Pk "$ROOT" | awk 'NR==2{print int($4/1024/1024)}')
[ "$free_gb" -ge 15 ] || die "only ${free_gb} GB free; about 15 GB is needed for images and build cache"
mkdir -p "$SECRETS" && chmod 700 "$SECRETS"
cd "$SMOKE"

# ---------------------------------------------------------------- 1. upstream repos at the tested commits
say "1/8 Cloning upstream repos into $ROOT (pinned to the commits that were tested)"
while read -r full sha _; do
  case "$full" in Polygant/*) ;; *) continue ;; esac
  repo="${full#Polygant/}"
  [ "$repo" = "OpenCEX" ] && continue                     # that's this checkout
  dir="$ROOT/$repo"
  if [ ! -d "$dir/.git" ]; then
    git clone -q "https://github.com/$full.git" "$dir"
    git -C "$dir" checkout -q "$sha"
    echo "   cloned $repo @ ${sha:0:7}"
  else
    echo "   $repo already present @ $(git -C "$dir" rev-parse --short HEAD)"
  fi
done < "$SMOKE/UPSTREAM_COMMITS.txt"

# ---------------------------------------------------------------- 2. backend patch
say "2/8 Applying backend patch"
BACKEND="$ROOT/OpenCEX-backend"
if git -C "$BACKEND" apply --check "$SMOKE/patches/backend.patch" 2>/dev/null; then
  git -C "$BACKEND" apply "$SMOKE/patches/backend.patch" && echo "   applied"
elif git -C "$BACKEND" apply -R --check "$SMOKE/patches/backend.patch" 2>/dev/null; then
  echo "   already applied"
else
  die "backend.patch does not apply to $BACKEND (local changes?)"
fi

# ---------------------------------------------------------------- 3. config
say "3/8 Writing config (random secrets, test values)"
if [ -f "$BACKEND/.env" ] && [ -f "$SMOKE/.env" ]; then
  echo "   keeping existing $BACKEND/.env"
else
  BACKEND_DIR="$BACKEND" FORCE=1 "$SMOKE/scripts/gen-env.sh"
fi

# ---------------------------------------------------------------- 4. images
say "4/8 Building images (first run: 5-15 minutes)"
SECRET_ARGS=()
CA_BUNDLE="${CA_BUNDLE:-/root/.ccr/ca-bundle.crt}"   # only exists behind a TLS-intercepting proxy
[ -r "$CA_BUNDLE" ] && SECRET_ARGS=(--secret "id=ca,src=$CA_BUNDLE")
DOCKER_BUILDKIT=1 docker build -q "${SECRET_ARGS[@]}" --build-arg "APT_PACKAGES=${APT_PACKAGES-gettext}" \
  -f "$SMOKE/docker/backend.Dockerfile" -t opencex:smoke "$BACKEND" >/dev/null
echo "   opencex:smoke built"
"$SMOKE/docker/build-frontends.sh" 2>&1 | grep -E "exit=|ERROR" | sed "s/^/   /"

# ---------------------------------------------------------------- 5. database
say "5/8 Starting database/broker and initialising"
docker compose up -d postgresql redis rabbitmq mailpit >/dev/null 2>&1
docker compose run --rm -T opencex python manage.py migrate --noinput >/dev/null 2>&1 || \
  { docker compose run --rm -T opencex python manage.py migrate --noinput | tail -20; die "migrate failed"; }
docker compose run --rm -T opencex python manage.py collectstatic --noinput >/dev/null 2>&1
echo "   migrations + static files done"
# wizard.py (blockchain part skipped). Its secrets file is streamed out instead of being left
# inside the web-served backend directory.
docker compose run --rm -T -e WIZARD_SKIP_BLOCKCHAIN=1 opencex sh -c \
  'python wizard.py >&2 && f=$(ls -t save_to_self_and_delete_*.txt | head -1) && cat "$f" && rm -f save_to_self_and_delete_*.txt' \
  > "$SECRETS/wizard-output.txt" 2>/dev/null || die "wizard.py failed (run it by hand to see why)"
chmod 600 "$SECRETS/wizard-output.txt"
echo "   wizard done (admin password saved in smoke-test/secrets/wizard-output.txt)"

# ---------------------------------------------------------------- 6. full stack
say "6/8 Starting the whole stack"
docker compose up -d >/dev/null 2>&1
for i in $(seq 1 90); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost/api/public/v1/info)" = 200 ] && break
  [ "$i" = 90 ] && die "site did not come up on http://localhost (is port 80 free?) - see: docker compose logs frontend opencex"
  sleep 2
done
echo "   http://localhost is up"

# ---------------------------------------------------------------- 7. trading data
say "7/8 Setting BTC-USDT reference price and creating demo users"
docker compose exec -T opencex python manage.py shell < "$SMOKE/scripts/set_custom_price.py" 2>/dev/null | tail -1
if [ ! -s "$SECRETS/demo-users.txt" ]; then
  pw() { python3 -c "import secrets; print('Demo-' + secrets.token_urlsafe(9))"; }
  printf 'alice@example.test %s\nbob@example.test %s\n' "$(pw)" "$(pw)" > "$SECRETS/demo-users.txt"
  chmod 600 "$SECRETS/demo-users.txt"
fi
DEMO_USERS=$(awk '{printf "%s%s:%s", (NR>1?",":""), $1, $2}' "$SECRETS/demo-users.txt")
docker compose exec -T -e DEMO_USERS="$DEMO_USERS" opencex python manage.py shell \
  < "$SMOKE/scripts/create_demo_users.py" 2>/dev/null | grep -E '^(created|exists)' | sed 's/^/   /'

# ---------------------------------------------------------------- 8. smoke test
if [ "${SKIP_SMOKE_TEST:-0}" != 1 ]; then
  say "8/8 Running the end-to-end trade test"
  COMPOSE_DIR="$SMOKE" python3 "$SMOKE/scripts/smoke_trade.py" > "$SECRETS/smoke_trade.out" 2>&1 \
    && echo "   RESULT: PASS (details: smoke-test/secrets/smoke_trade.out)" \
    || { tail -25 "$SECRETS/smoke_trade.out"; die "smoke test FAILED"; }
fi

admin_pw=$(grep -oP 'Email: \S+  Password: \K\S+' "$SECRETS/wizard-output.txt" | head -1 || true)
cat <<EOF

========================================================================
 OpenCEX is running. Open these in your browser:

   Exchange (log in + trade)  http://localhost/account/login
       then BTC-USDT market   http://localhost/account/trade/BTC-USDT
   Public site                http://localhost/
   Admin panel                http://localhost/admin/
   Test inbox (Mailpit)       http://localhost:8025   <- sign-up codes land here

 Demo traders (1 BTC + 100,000 USDT each, play money):
$(sed 's/^/   /' "$SECRETS/demo-users.txt")
 Admin: admin@example.com  ${admin_pw:-(see smoke-test/secrets/wizard-output.txt)}

 Stop:   cd $SMOKE && docker compose stop
 Start:  cd $SMOKE && docker compose start
 Wipe:   cd $SMOKE && docker compose down -v
========================================================================
EOF

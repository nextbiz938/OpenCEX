#!/usr/bin/env bash
# Non-interactive replacement for opencex.sh steps 1-12 (the `read -p` wizard).
# Renders <backend>/.env from the backend's .env.template with TEST values only,
# and writes smoke-test/.env (compose interpolation: DB/AMQP creds + paths).
# Secrets are generated randomly on each run and never committed (.env is gitignored).
#
# Usage: BACKEND_DIR=/path/to/OpenCEX-backend ./gen-env.sh   (refuses to overwrite unless FORCE=1)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${BACKEND_DIR:-$(cd "$HERE/../../OpenCEX-backend" 2>/dev/null && pwd || echo /app/opencex/backend)}"
OUT="$BACKEND_DIR/.env"
if [ -f "$OUT" ] && [ "${FORCE:-0}" != 1 ]; then echo "$OUT exists; set FORCE=1 to regenerate (this rotates DB/AMQP passwords!)"; exit 1; fi
rnd() { python3 -c "import secrets,string,sys; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(int(sys.argv[1]))))" "$1"; }

set -a
# STEP 1 project
PROJECT_NAME=OpenCEXSmoke
DOMAIN=${DOMAIN:-localhost}
ADMIN_BASE_URL=admin
ADMIN_USER=${ADMIN_USER:-admin@example.com}
ADMIN_MASTERPASS=$(rnd 24)
SUPPORT_EMAIL=support@example.com
TELEGRAM=opencex; FACEBOOK=polygant; TWITTER=polygant; LINKEDIN=polygant; LOGO=; TG_NEWS=
# NEW: Django SECRET_KEY (upstream hardcodes it in exchange/settings/common.py; see patches/backend)
SECRET_KEY=$(rnd 64)
# STEP 2 common services: Google's public reCAPTCHA *test* keys (always validate).
RECAPTCHA=6LeIxAcTAAAAAJcZVRqyHh4FAAAAAAAAAAAA4
RECAPTCHA_SECRET=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
# NEW (patched setting): registration ALWAYS calls google.com/recaptcha/api/siteverify; google.com is blocked
# in the sandbox, so captcha is off here. On a VPS with internet use CAPTCHA_ENABLED=True (test keys always pass).
CAPTCHA_ENABLED=${CAPTCHA_ENABLED:-False}
# Upstream leaves this empty, and re.match('', ip) matches every IP => captcha is never required.
# Here: bypass only for docker-internal 172.16/12 addresses (google.com is unreachable from the sandbox).
CAPTCHA_ALLOWED_IP_MASK=${CAPTCHA_ALLOWED_IP_MASK:-'^172\.(1[6-9]|2[0-9]|3[01])\.'}
TELEGRAM_CHAT_ID=; TELEGRAM_ALERTS_CHAT_ID=; TELEGRAM_BOT_TOKEN=
# STEP 3 blockchain APIs: none (no mainnet)
INFURA_API_KEY=; INFURA_API_SECRET=; ETHERSCAN_KEY=; CRYPTOCOMPARE_API_KEY=
# STEP 4 safe addresses: public TEST-VECTOR addresses only (BIP84 testnet vector; Anvil/Hardhat account #0)
BTC_SAFE_ADDR=tb1q6rz28mcfaxtmd6v789l9rrlrusdprr9pqcpvkl
ETH_SAFE_ADDR=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
# STEP 5-7 optional chains: off
ENABLED_BNB=False; BSCSCAN_KEY=; BNB_SAFE_ADDR=
ENABLED_TRON=False; TRONGRID_API_KEY=; TRX_SAFE_ADDR=
ENABLED_MATIC=False; POLYGONSCAN_KEY=; MATIC_SAFE_ADDR=
# STEP 8 email -> local Mailpit (no auth, no TLS)
EMAIL_HOST=mailpit; EMAIL_HOST_USER=noreply@example.com; EMAIL_HOST_PASSWORD=; EMAIL_PORT=1025; EMAIL_USE_TLS=False
# STEP 9-12 optional services: off
IS_SMS_ENABLED=False; IS_KYC_ENABLED=False; IS_KYT_ENABLED=False; IS_HUMMINGBOT_ENABLED=False
# auto-generated section of opencex.sh
INSTANCE_NAME=opencex
DB_NAME=opencex; DB_USER=opencex; DB_PASS=$(rnd 24); DB_HOST=postgresql; DB_PORT=5432
AMQP_USER=opencex; AMQP_PASS=$(rnd 24); AMQP_HOST=rabbitmq; AMQP_PORT=5672; RMQDOMAIN=
BTC_NODE_USER=opencex; BTC_NODE_PASS=$(rnd 24); BTC_NODE_PORT=8332; BTC_NODE_HOST=bitcoind
REDIS_HOST=redis; REDIS_PORT=6379; REDIS_PASS=
BOTS_API_BASE_URL=http://opencex:8080
CRYPTO_KEY=$(rnd 32)
BOT_PASSWORD=$(rnd 16)
DEBUG=; IS_TEST=; SENTRY_DSN=; CRYPTO_KEY_OLD=
set +a

# envsubst equivalent (envsubst/gettext-base may be missing on the host)
python3 - "$BACKEND_DIR/.env.template" "$OUT" <<'PY'
import os, re, sys
src = open(sys.argv[1]).read()
out = re.sub(r'\$\{(\w+)\}', lambda m: os.environ.get(m.group(1), ''), src)
open(sys.argv[2], 'w').write(out)
PY
# opencex.sh also appends the frontend values to backend/.env
cat >> "$OUT" <<EOT


#opencex frontend values
RECAPTCHA=$RECAPTCHA
TELEGRAM=$TELEGRAM
TG_NEWS=$TG_NEWS
SUPPORT_EMAIL=$SUPPORT_EMAIL
FACEBOOK=$FACEBOOK
TWITTER=$TWITTER
LINKEDIN=$LINKEDIN
EOT
chmod 600 "$OUT"

# compose interpolation file (gitignored)
cat > "$HERE/.env" <<EOT
BACKEND_DIR=$BACKEND_DIR
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASS=$DB_PASS
AMQP_USER=$AMQP_USER
AMQP_PASS=$AMQP_PASS
EOT
chmod 600 "$HERE/.env"
echo "wrote $OUT and $HERE/.env"

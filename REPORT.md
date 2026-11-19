# OpenCEX smoke test — report

**Result: PASS.** A crossing BTC-USDT limit buy and sell between two freshly registered users executed through the real matching engine (`bin/stack.py`), and both users' balances moved by exactly the expected amounts, including the 0.1% limit-order fee.

- Date: 2026-11-19
- Where: throwaway cloud VM (4 vCPU / 16 GB / Ubuntu 24.04 / Docker 29.10)
- Test values only. No real keys, wallets or funds. No mainnet connections.
- Everything needed to rebuild the stack is in `smoke-test/` on branch `opencex-smoke-test`.
- **Screenshot tour (79 images):** [smoke-test/screenshots/README.md](smoke-test/screenshots/README.md) covers sign-up/sign-in, wallet, test deposits and withdrawals, trading and charts, and the admin panel. See [How to reuse on a VPS](#how-to-reuse-on-a-vps).

## Upstream commits tested

From `smoke-test/UPSTREAM_COMMITS.txt`:

| Repo | Commit | Date |
|---|---|---|
| Polygant/OpenCEX (installer) | 12d721419cc4cf1378f43be3514cfe982a3d3515 | 2026-03-19 (README edits; last code change is "Release 1.5.1") |
| Polygant/OpenCEX-backend | 927b333d2c0e7ef961516e62a711c6d9629cd6aa | 2026-03-19 |
| Polygant/OpenCEX-frontend | a5c0bbe9c47492f733993ddef82b398bd8a38422 | 2026-03-19 |
| Polygant/OpenCEX-JS-admin | c1d9cd5ea042d4889d90e48a46f1aeb3c1c6a9d4 | 2026-03-19 |
| Polygant/OpenCEX-static (nuxt) | f315c3a7c11aa825b0aac45d9bd583a702008a28 | 2026-03-19 |

## 1. What `opencex.sh` does

I read the script and did not run it. In order:

1. Installs Docker CE from download.docker.com if it is missing.
2. Clones backend, frontend, static (nuxt) and admin into `/app/opencex/{backend,frontend,nuxt,admin}`. It expects the installer repo itself at `/app/deploy`.
3. Runs a 12-step `read -p` wizard: project name, domain, admin email, master password, reCAPTCHA keys, Telegram, Infura and Etherscan keys, BTC and ETH "safe" (cold) addresses, optional BSC/Tron/Polygon, SMTP, Twilio, Sumsub KYC, Scorechain KYT, Hummingbot. It also generates random DB, RabbitMQ, bitcoind, CRYPTO_KEY and bot passwords, then `envsubst`s `backend/.env.template` into `backend/.env`.
4. Renders the frontend `src/local_config`, nuxt `.env` and admin `src/local_config.js`. It appends the frontend values to `backend/.env`.
5. Builds four images: `frontend` (node:18 to nginx:alpine; the nginx also reverse-proxies everything), `nuxt` (node:14.18.1), `admin` (node:18 to nginx:alpine) and `opencex` (the backend repo's own Dockerfile, python:3.8). The installer's `backend/Dockerfile` (with wkhtmltopdf) is **not** used.
6. Writes `docker-compose.yml` with 19 services:
   - `opencex` (gunicorn :8080), `opencex-wss` (daphne)
   - `opencex-cel`: Celery worker plus beat, excluding blockchain queues
   - `opencex-stack`: the matching engine, a Celery worker on the `orders.<PAIR>` queues
   - `opencex-btc` (btcworker), plus ten blockchain Celery workers (blocks, deposits, payouts, balances, accumulations, gas)
   - `frontend`, `nuxt`, `admin`
   - `caddy` (lucaslorentz/caddy-docker-proxy:latest), `postgres:latest`, `redis:latest`, `rabbitmq:3.9.22-management`, `lncm/bitcoind:v24.0.1`
   - It creates the data directories with `chmod 777`.
7. `docker compose up -d`, then `migrate` and `collectstatic`.
8. Writes `bitcoin.conf` (`prune=20000`, `rpcallowip=0.0.0.0/0`), creates a legacy bitcoind wallet, runs `wizard.py` and restarts the stack.
9. POSTs `{"domain": ...}` to `http://alertbot.plgdev.com/registration`. **I skipped this, as instructed.**

`wizard.py` does the following, all inside one `atomic()` block:
- CoinInfo, FeesAndLimits and WithdrawalFee for ETH, BTC, USDT, BNB, TRX and MATIC.
- DisabledCoin rows for the disabled chains.
- A market-maker bot user `bot1@bot.com`, topped up with 3 BTC and 100k USDT among others.
- Five pairs, each with PairSettings (`price_source=External`, deviation 0.99) and a BotConfig.
- A superuser for `ADMIN_USER` (random password plus a TOTP device) and the Django Site.
- **Blockchain part:** the current BTC **mainnet** block height from `https://blockchain.info/latestblock` (`cryptocoins/coin_service.py:553`), a BTC multisig keeper (which needs bitcoind RPC), and hot-wallet keepers for ETH, BNB, TRX and MATIC.
- It writes the secrets to `save_to_self_and_delete_<ts>.txt` in the backend directory.

## 2. What I ran instead

| Step | How |
|---|---|
| Config | `smoke-test/scripts/gen-env.sh` writes the same variables as the wizard, non-interactively. Secrets are random and land in gitignored `.env` files with mode 600. |
| Test values | `DOMAIN=localhost`, `ADMIN_BASE_URL=admin`, `ADMIN_USER=admin@example.com`, a random 64-char `SECRET_KEY`, Google's public reCAPTCHA **test** keys, SMTP to Mailpit (`mailpit:1025`, no auth or TLS), all chain API keys empty, BNB/TRON/MATIC disabled. The "safe" addresses are public test vectors: the BIP84 testnet vector `tb1q6rz2…pvkl` and Anvil/Hardhat account #0 `0xf39F…2266`. |
| Images | `smoke-test/docker/*.Dockerfile` plus `docker/build-frontends.sh`. Tags: `opencex:smoke`, `opencex-frontend:smoke`, `opencex-nuxt:smoke`, `opencex-admin:smoke`. |
| Stack | `smoke-test/docker-compose.yml`. Pinned `postgres:14`, `redis:7`, `rabbitmq:3.9.22-management`, `axllent/mailpit:v1.21.8`, `nginx:1.27-alpine`. No Caddy and no bitcoind. The blockchain workers sit behind the opt-in `chains` profile. Ports are bound to 127.0.0.1: 80 (site), 8080 (API), 8025 (Mailpit), 15672 (RabbitMQ UI). |
| DB setup | `migrate` (63 migrations OK), `collectstatic` (454 files), then `WIZARD_SKIP_BLOCKCHAIN=1 python wizard.py`, which is the patched wizard minus its blockchain part. |
| Pricing | `scripts/set_custom_price.py`: BTC-USDT `price_source=Custom`, `custom_price=30000`. See failure F8. |

Running services: postgresql, redis, rabbitmq, mailpit, opencex, opencex-wss, opencex-cel, opencex-stack, nuxt, admin, frontend.

## 3. What worked

- **All four images build.**
  - backend: 2.13 GB, about 2 minutes cold
  - nuxt: 2.2 GB, 102 s
  - frontend: 99 MB, 75 s
  - admin: 81 MB, 53 s
- **Migrations and collectstatic run clean.** The wizard's non-blockchain part also runs once two patches are applied.
- **Every web route answers through the frontend nginx on `http://localhost`:**
  - `/` (nuxt SSR): 200
  - `/account/` (SPA): 200
  - `/admin/` (admin SPA): 200
  - `/api/public/v1/info`: 200
  - `/apiadmin/`: 401 anonymous, 200 as admin
  - `/staticfiles/…`: 200
  - `/wsapi/v1/live_notifications`: 101 Switching Protocols (daphne)
- **Registration** works: `POST /api/v1/auth/registration/` returns 201.
- **Email confirmation** works. The confirmation mail arrives in Mailpit with subject "[OpenCEXSmoke] Email Confirmation" and a **6-digit code, not a link**. `POST /api/v1/auth/registration/verify-email/ {"key": code}` returns 200.
- **Login:** `POST /api/v1/auth/login/` returns a JWT, which is signed with the new per-install SECRET_KEY. Before confirmation, login is correctly refused with 400 `email_not_verified`.
- **Admin:** the wizard-created superuser logs in and `/apiadmin/` lists the admin resources.
- **Test balances:** credited through the same ledger call wizard.py uses: `Transaction.topup(..., reason=REASON_MANUAL_TOPUP)` plus `create_or_update_wallet_history_item_from_transaction`.
- **The trade.** User A sold and user B bought 0.01 BTC at 30000 USDT. Both orders went to `state=1` (closed) with `quantity_left=0`, and two `ExecutionResult` rows were written. Balances from `GET /api/v1/balance/`:

  | | BTC before | BTC after | USDT before | USDT after |
  |---|---|---|---|---|
  | A (seller, maker) | 2.00000 | 1.99000 (−0.01) | 0 | 299.70 (+300 − 0.30 fee) |
  | B (buyer, taker) | 0 | 0.00999 (+0.01 − 0.00001 fee) | 100000 | 99700.00 (−300) |

  - Fees are 0.1% on each side (`fee_order_limits=0.001` from wizard.py), recorded on the executions: 0.00001 BTC and 0.30 USDT.
  - A started with 2 BTC because my first manual credit run topped A up once before failing on the second (not yet registered) user.
  - The fees were **not** credited to `FEE_USER` at match time; FEE_USER's balance was still empty right after the trade. My inference, not tested: the daily `aggregate_fee` beat task (04:01) sweeps them later.

- **Repeatable end-to-end script:** `smoke-test/scripts/smoke_trade.py` (see section 6) passed with fresh users. Matching took about 1 s after the buy was placed.
- **Market-maker bots** (wizard's `bot1@bot.com`) stop with "External price unavailable". They would not interfere anyway: bot orders sit in a separate book and never match user orders (`core/orderbook/book.py:22`).

## 4. What failed, with exact errors

| # | Where | Exact error | Cause | Fix |
|---|---|---|---|---|
| F1 | backend build, first `docker build` | `failed to resolve source metadata for docker.io/library/python:3.8: unexpected status from HEAD request … 429 Too Many Requests` | Docker Hub rate-limits the shared VM IP (sandbox) | dockerd `registry-mirrors: ["https://mirror.gcr.io"]` |
| F2 | pip and yarn in builds | `SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain'))` | Egress goes through a TLS-intercepting proxy (sandbox) | Optional BuildKit secret `ca`, used as `PIP_CERT` / `NODE_EXTRA_CA_CERTS` only during installs. It is a no-op on a VPS. |
| F3 | backend `pip install -r requirements.txt` | `ERROR: Cannot install Twisted==23.10.0rc1, twisted[tls]==22.10.0, … because these package versions have conflicting dependencies.` | **Upstream bug:** a pre-release is pinned, while `daphne==4.0.0` needs `twisted[tls]>=22.4`, which pip won't satisfy with an rc | `Twisted==23.10.0` (the final release) |
| F4 | backend `apt-get install systemd gettext` | `E: Package 'gettext' has no installation candidate` | `deb.debian.org` is blocked by sandbox egress | Made the step optional (`--build-arg APT_PACKAGES=`). gettext is only needed for `compilemessages`, which the installer never runs. Dropped systemd, which is useless in a container. |
| F5 | `wizard.py` | `django.db.utils.IntegrityError: duplicate key value violates unique constraint "core_disabledcoin_currency_key"` / `DETAIL: Key (currency)=(7) already exists.` | **Upstream bug:** the `if not IS_MATIC` block appends MATIC's DisabledCoin to `coin_info[TRX]`, so `get_or_create` writes a second TRX row. It hits **every** install that answers False/blank for both Tron and Polygon, which is the default. The whole wizard rolls back. | Append to `coin_info[MATIC]` |
| F6 | `wizard.py` blockchain part | Not run. It fetches the BTC mainnet height from `https://blockchain.info/latestblock` inside the same `atomic()`, then builds a BTC multisig keeper through bitcoind RPC. With no internet and no node, the whole wizard would roll back. | Requires internet and bitcoind | `WIZARD_SKIP_BLOCKCHAIN=1` skips the BTC block height and the keeper generation |
| F7 | registration captcha | `curl: (56) CONNECT tunnel failed, response 403` for `www.google.com` (sandbox egress). From inside containers there is no external DNS at all. | `CAPTCHA_ENABLED = True` is hardcoded, and registration **always** verifies with Google (`skip_extra_checks=True`; the IP-mask bypass does not apply) | Made `CAPTCHA_ENABLED` an env setting, False for this test. On a VPS, Google's test keys pass with it True. |
| F8 | first order | `{"message":{"message":"no last price and no custom price","code":"invalid"},"type":{"message":"invalid_last_or_custom_price","code":"invalid"}}` | wizard.py sets `price_source=External`, and the price feeds (`min-api.cryptocompare.com`, `api.binance.com`) are unreachable | Set the pair to a Custom price of 30000, as an operator would in the admin panel |
| F9 | second registration | `{"username":{"message":{"message":"similar username was recently used",…},"type":{"message":"registration_similar_username",…}}}` | By design: rejects emails scoring ≥85 (`fuzz.token_sort_ratio`) against the last 5 usernames | Use dissimilar test emails (`smoke_trade.py` randomises them) |
| F10 | `opencex-cel` logs (non-fatal) | `HTTPSConnectionPool(host='min-api.cryptocompare.com', port=443): … [Errno -2] Name or service not known`; `bots.bot Bot Exception: … External price unavailable … BTC-USDT`; `cryptocoins.tasks.btc Can't calculate satoshi per byte` | No internet or bitcoind. The market-maker bots stop, which kept them out of the trade test. | None needed |
| F11 | `opencex-btc` (btcworker), run once for 60 s | It started a Celery worker for the `btc` queue and logged `celery@… ready.` I saw no crash and no error in that window; RPC failures would surface only when a `btc` task runs. | No bitcoind | Kept behind the `chains` profile |
| F12 | Admin panel action buttons (Make Topup, Confirm email, Approve, ...) | Clicking DO sends nothing; the action URL the API advertises is `https://localhost/apiadmin/admin_rest/exchangeuser/topup/` | **Upstream config bug:** nginx hard-codes `X-Forwarded-Proto: https`, so on plain http Django builds `https://` URLs and the browser can't reach them | `frontend-default.conf` now forwards the real scheme (or an outer TLS proxy's header). After the fix, Make Topup returns 200. |
| F13 | BTC (any non-USDT) withdrawal | HTTP **500**; log: `TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'NoneType'` at `core/serializers/withdrawal.py:112`. The UI shows nothing. | **Upstream bug:** the monthly-limit check multiplies by the external price cache, which is `None` when the price feed is unreachable | Not patched. USDT withdrawals work (no conversion needed); with internet the price feed fills the cache. |
| F14 | BTC deposit address | "Create" spins forever | BTC deposit addresses come from bitcoind (not running) | Expected. ETH and ERC-20 USDT addresses are generated offline and work. |

I did not start the ETH/BNB/TRX/MATIC scanners (`opencex-eth-blocks`, `-deposits`, `-payouts`, …). They only talk to mainnet endpoints (see section 7), so they stay disabled behind the `chains` profile.

## 5. Every change and why

### Backend patches (`smoke-test/patches/backend.patch`, applies to OpenCEX-backend@927b333)

1. **`requirements.txt`:** `Twisted==23.10.0rc1` → `23.10.0` (F3).
2. **`exchange/settings/common.py`:** `SECRET_KEY = env('SECRET_KEY')` replaces the hardcoded key. **Security:** every stock install shares the same Django `SECRET_KEY`, which is also SimpleJWT's `SIGNING_KEY`, so anyone can forge access tokens for any OpenCEX site. `.env.template` gets a `SECRET_KEY` line.
3. **`exchange/settings/auth.py`:** `CAPTCHA_ENABLED = env('CAPTCHA_ENABLED', default=True, cast=bool)` (F7). `.env.template` gets a line for it.
4. **`wizard.py`:**
   - MATIC DisabledCoin bug fix (F5).
   - `WIZARD_SKIP_BLOCKCHAIN` switch around the bitcoind/keeper section (F6). The rest of the wizard is unchanged.
5. **`exchange/celery_app.py`:** don't schedule `cryptocoins.tasks.trx.get_trc20_unit_price` or `retry_unknown_withdrawals` when `COMMON_TASKS_TRON=False`. Upstream polls **TRON mainnet** (TronGrid) every hour even with Tron disabled.

### Deployment changes (`smoke-test/`)

6. **`docker-compose.yml`:** I added `eth_collect_dust` to the general worker's `-X` list. Upstream's general worker consumes `ETH_accumulate_dust` every 10 minutes, which calls **ETH mainnet via Infura**, even though every other ETH queue is excluded. Other differences from the installer's compose:
   - pinned images
   - healthchecks with `depends_on: service_healthy`
   - named volumes instead of `chmod 777` directories
   - `restart: unless-stopped`
   - blockchain workers behind `profiles: [chains]`
   - ports bound to 127.0.0.1
   - Mailpit added; Caddy and bitcoind removed
7. **`docker/frontend-default.conf`:**
   - **Security fix, nginx alias traversal.** Upstream has `location /media { alias /app/media/; }` and `location /upload { alias /app/media/; }`, and the frontend container mounts the backend directory at `/app`. Once `/app/media` exists (Django creates it on the first upload, such as KYC documents or a logo), `GET /media../<file>` serves any world-readable file in the backend directory. I verified it here: `/media../traversal-canary.txt` and `/media../wizard.py` returned **200**.
     - On a stock install that includes `.env` (mode 644 from `envsubst`). It holds DB_PASS, AMQP_PASS, CRYPTO_KEY (which encrypts the hot-wallet private keys) and ADMIN_MASTERPASS.
     - It also includes `save_to_self_and_delete_*.txt`: the admin password and the keeper wallet passwords.
     - Fixed with `location /media/` and `location /upload/`. Re-verified: the traversal now returns 404 while `/media/ok.txt` returns 200.
   - **Fix, `X-Forwarded-Proto`:** forward the real scheme instead of a hard-coded `https` (F12). Without it, every admin-panel action button is dead on a plain-http install.
   - `resolver 127.0.0.11` plus variable `proxy_pass`, so nginx starts even when an upstream container is down. Upstream's nginx refuses to start in that case.
8. **`config/`:**
   - All URLs use `http://localhost` and `ws://` (there is no TLS without Caddy).
   - Nuxt's server-side `API_URL` is `http://opencex:8080/`, because `localhost` inside the nuxt container is the container itself.
9. **Dockerfiles:**
   - pinned base images (`python:3.8-bookworm`, `node:18`, `node:14.18.1`, `nginx:1.27-alpine`)
   - optional CA secret (F2)
   - dependency layers cached before `COPY .`
   - `.dockerignore` files
   - the optional apt step (F4)
10. **`scripts/gen-env.sh`:**
    - `CAPTCHA_ALLOWED_IP_MASK` is set to Docker's 172.16/12 range. **Security:** upstream leaves it as `""`, and `re.match("", ip)` matches every IP, so **login captcha is never required on a stock install** (`core/serializers/auth.py:137`).
    - Writes `.env` with mode 600.
11. **Data, not code:**
    - BTC-USDT set to a custom price of 30000 (`scripts/set_custom_price.py`).
    - Test users credited with `scripts/credit_balances.py`.
    - The wizard's secrets file was moved out of the backend directory.

### Sandbox-only changes (not needed on a normal VPS)

- Started `dockerd` by hand.
- Configured the `mirror.gcr.io` registry mirror.
- Passed the proxy CA as a build secret.
- Built with `APT_PACKAGES=` (empty).
- Set `CAPTCHA_ENABLED=False`.

### Other upstream observations (not changed)

- `PASSWORD_MIN_LENGTH = 1` (`exchange/settings/auth.py`).
- Withdrawals need a 6-digit code emailed to the user, then admin approval. New users may withdraw at most 100 USDT-equivalent per month (limit level 0, adjustable by the admin).
- The installer:
  - uses `:latest` for postgres, redis and caddy
  - exposes the RabbitMQ management UI through Caddy (`RMQDOMAIN` label)
  - sets `rpcallowip=0.0.0.0/0` for bitcoind
  - `chmod 777`s all data directories
- The backend image runs Celery as root (`SecurityWarning: You're running the worker with superuser privileges`).
- Both `wizard.py` and the installer write long-lived secrets as plaintext files in the web-served backend directory. That is what makes F-security #7 exploitable.

## 6. How the trade test is run

```bash
cd smoke-test
python3 scripts/smoke_trade.py
```

The script:
1. Registers two random users.
2. Reads the confirmation codes from the Mailpit API and verifies them.
3. Logs both users in.
4. Credits balances through `docker compose exec opencex python manage.py shell < scripts/credit_balances.py`.
5. Places a limit SELL and a limit BUY of 0.01 BTC @ 30000.
6. Polls until both orders close.
7. Asserts the balance deltas, including fees.

It exits non-zero on failure.

**Final run: `RESULT: PASS`, exit 0, 5.6 s.** The full output (passwords removed) is in `smoke-test/results/smoke_trade.out`:

```
user cur               before              after            delta         expected
A    BTC           1.00000000         0.99000000      -0.01000000      -0.01000000  OK
A    USDT     100000.00000000    100299.70000000     299.70000000     299.70000000  OK
B    BTC           1.00000000         1.00999000       0.00999000       0.00999000  OK
B    USDT     100000.00000000     99700.00000000    -300.00000000    -300.00000000  OK
exchange fee collected: 0.30000000 USDT (from A) + 0.00001000 BTC (from B)
```

The script's other knobs:
- `CREDIT_MODE=manual|skip` lets you credit balances yourself.
- `REGISTER_MODE=orm` uses `scripts/orm_register.py` if the registration API is blocked.
- `credit_balances.py` refuses to credit anyone outside `@example.test`.

## 7. Resources

- **RAM at idle:** about 1.3 GB for all 11 containers (`docker stats`). The largest are `opencex-cel` at 380 MB, `opencex` (gunicorn ×2) at 222 MB and frontend nginx at 171 MB; everything else is under 150 MB. Host `used` was 2.3 GB.
  - The installer's 16 GB recommendation is about bitcoind and the JS builds, not the runtime. Building three JS images in parallel next to the backend fit easily in 16 GB.
  - A full stock install adds about 10 more worker containers at roughly 140–380 MB each, plus bitcoind.
- **Disk:** about 13 GB in total, measured as root fs usage going from 8.9 GB before to 22 GB after.
  - images: 7.3 GB (backend 2.13 GB, nuxt 2.2 GB, infra about 1.2 GB, node build bases)
  - build cache: 8.1 GB (partly shared with the images)
  - volumes: about 59 MB
  - `docker builder prune` after building reclaims most of the cache.
  - Free space never dropped below 47 GB, so the 3 GB stop rule never triggered.

## 8. What deposits and withdrawals would still need

Every chain integration points at **mainnet**, with addresses or endpoints hardcoded in code rather than in `.env`. Each needs a local devnet plus a small patch.

| Chain | Hardcoded today | Needed for a local test |
|---|---|---|
| **BTC** | Node via `BTC_NODE_*` env (good). Address codec is `cryptos.Bitcoin()` in mainnet mode (`cryptocoins/coins/btc/service.py:29`, `cryptocoins/utils/btc.py:47`), and `CRYPTO_TESTNET = False`. | `bitcoind -regtest` (e.g. `lncm/bitcoind` with `regtest=1`, `rpcport=18443`, `fallbackfee`). Patch the codec to `Bitcoin(testnet=True)` (regtest shares testnet's legacy prefixes; bech32 `bcrt1` needs checking). Patch `get_last_network_block_id` (`cryptocoins/coin_service.py:553`) to ask the local node (`getblockcount`) instead of blockchain.info mainnet. Create the legacy wallet as the installer does, then rerun `wizard.py` without `WIZARD_SKIP_BLOCKCHAIN` to set the last block and create the BTC multisig keeper. Run `opencex-btc` and mine blocks with `generatetoaddress`. |
| **ETH / ERC-20** | `https://mainnet.infura.io/v3/{INFURA_API_KEY}` (`cryptocoins/utils/infura.py:21`), `ETH_CHAIN_ID = 1`, USDT contract `0xdAC17F…1ec7` (`cryptocoins/coins/usdt/__init__.py:10`) | **Anvil** (`anvil --chain-id 31337`). Patch the provider URL and chain id to env (e.g. `ETH_RPC_URL`, `ETH_CHAIN_ID`). Deploy a mock 6-decimal USDT and point the token config at it (or use `manage.py add_token`). Let wizard create the ETH keeper and GasKeeper, fund them from Anvil's prefunded accounts, then run `opencex-eth-blocks`, `-deposits`, `-payouts`, `-balances`, `-coin/token-accumulations` and `-gas`. |
| **TRX / TRC-20** | `Tron(HTTPProvider(api_key=TRONGRID_API_KEY))`, which is TronGrid mainnet (`cryptocoins/coins/trx/tron.py:56`, also `trx/utils.py:31` and the cold-wallet stats handlers). USDT contract `TR7NHq…jLj6t`. | **tronbox/tre** (local Tron devnet). Patch the clients to `HTTPProvider(endpoint_uri=env('TRON_RPC_URL'))`. Deploy a TRC-20 mock and update its address. Set `COMMON_TASKS_TRON=True` and fund the keepers. |
| **BNB / BEP-20** | `BNB_RPC_ENDPOINTS` (list of bsc-dataseed mainnet URLs) and `BNB_CHAIN_ID = 56` in `exchange/settings/crypto.py`, plus the USDT contract `0x55d398…7955` | A second Anvil instance (any chain id). Patch both settings to env. |
| **MATIC** | `POLYGON_RPC_URL` env with default `polygon-rpc.com` (already configurable), `MATIC_CHAIN_ID = 137` | Anvil with `POLYGON_RPC_URL`, plus a chain-id patch |

Also needed:
- Withdrawals go through the admin approve endpoints (`/apiadmin/cryptocoins/*withdrawalapprove/`), which need the keeper password from the wizard's secrets file.
- The beat tasks `sci_process_withdrawals` and `cancel_expired_withdrawals` must run (the `payout_withdraw` queue, consumed by the general worker).
- KYT (Scorechain) and KYC (Sumsub) are external SaaS and must stay disabled.

## How to reuse on a VPS

```bash
git clone -b opencex-smoke-test <this repo> OpenCEX
for r in OpenCEX-backend OpenCEX-frontend OpenCEX-JS-admin OpenCEX-static; do git clone https://github.com/Polygant/$r; done   # pin to UPSTREAM_COMMITS.txt
git -C OpenCEX-backend apply ../OpenCEX/smoke-test/patches/backend.patch
cd OpenCEX/smoke-test
DOMAIN=localhost scripts/gen-env.sh
docker build -f docker/backend.Dockerfile -t opencex:smoke ../../OpenCEX-backend
docker/build-frontends.sh
docker compose up -d postgresql redis rabbitmq mailpit
docker compose run --rm opencex python manage.py migrate
docker compose run --rm opencex python manage.py collectstatic --noinput
docker compose run --rm -e WIZARD_SKIP_BLOCKCHAIN=1 opencex python wizard.py   # then move save_to_self_and_delete_*.txt out of the backend dir!
docker compose up -d
docker compose exec -T opencex python manage.py shell < scripts/set_custom_price.py
python3 scripts/smoke_trade.py
```

For a public VPS:
- Set `CAPTCHA_ENABLED=True` with real reCAPTCHA keys and a real `DOMAIN`.
- Put TLS (Caddy or similar) in front of port 80.
- Replace Mailpit with a real SMTP relay.
- Remove the `127.0.0.1:8080`, `:8025` and `:15672` port mappings.

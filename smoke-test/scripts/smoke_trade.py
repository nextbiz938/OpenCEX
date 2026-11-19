#!/usr/bin/env python3
"""OpenCEX end-to-end trade smoke test (TEST values only).

register A+B (API) -> confirmation code from Mailpit -> verify-email (API) -> login (JWT)
-> credit A/B via Django shell (credit_balances.py, ledger-consistent) -> A limit SELL, B limit BUY
-> wait for the matching engine (bin/stack.py, queue orders.<PAIR>) -> fee-aware balance assertions.

Stdlib only. Run from the host:
    python3 smoke_trade.py                      # defaults below
    CREDIT_MODE=manual python3 smoke_trade.py   # pause and let you credit by hand

Env / flags (flag wins):
  BASE_URL      http://localhost            frontend nginx (proxies /api -> backend)
  MAILPIT_URL   http://localhost:8025
  COMPOSE_DIR   /home/user/OpenCEX/smoke-test
  SERVICE       opencex                     compose service used for `manage.py shell`
  DJANGO_SHELL_CMD  "docker compose exec -T $SERVICE python manage.py shell"  (run in COMPOSE_DIR; "-c <code>" appended)
  PAIR BTC-USDT  PRICE 30000  QTY 0.01  TIMEOUT 60  COUNTRY DE
  CREDIT_MODE   docker | manual | skip      (default docker)
  REGISTER_MODE auto | api | orm            (default auto: API, fall back to orm_register.py on captcha/5xx)

Exit codes: 0 PASS, 1 FAIL, 2 trade PASS but registration needed the ORM fallback.
"""
import argparse
import base64
import json
import os
import re
import secrets
import shlex
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_DOWN

HERE = os.path.dirname(os.path.abspath(__file__))
Q8 = Decimal('0.00000001')
TOL = Decimal('0.00000002')  # JSON floats -> allow 2 satoshi of slack
ORDER_STATES = {0: 'opened', 1: 'closed', 2: 'cancelled', 3: 'reverted'}


class SmokeFailure(Exception):
    pass


def D(x):
    return Decimal(str(x if x is not None else 0))


def q8(x):
    return D(x).quantize(Q8, rounding=ROUND_DOWN)


def fmt(x):
    return f'{q8(x):f}'


def jdump(o):
    return json.dumps(o, default=str)


def log(msg):
    print(msg, flush=True)


def step(msg):
    log(f'\n==> {msg}')


# ---------------------------------------------------------------- HTTP
def http(method, url, data=None, token=None, timeout=60):
    headers = {'Accept': 'application/json', 'User-Agent': 'opencex-smoke-test/1.0', 'X-API-LANG': 'en'}
    body = None
    if data is not None:
        body = json.dumps(data, default=str).encode()
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except OSError as e:  # URLError, timeouts, connection refused
        return 0, {'_error': f'{type(e).__name__}: {e}'}
    text = raw.decode('utf-8', 'replace')
    if not text:
        return status, None
    try:
        return status, json.loads(text, parse_float=Decimal)
    except ValueError:
        return status, {'_raw': text[:1500]}


class Api:
    def __init__(self, base_url):
        self.base = base_url.rstrip('/') + '/api/v1/'

    def __call__(self, method, path, data=None, token=None, timeout=60):
        return http(method, self.base + path.lstrip('/'), data=data, token=token, timeout=timeout)


# ---------------------------------------------------------------- helpers
def rand_alnum(n):
    a = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(a) for _ in range(n))


def _lcs(a, b):
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def similarity(a, b):
    """~fuzzywuzzy token_sort_ratio (python-Levenshtein). Registration rejects >=85 vs the last 5 users
    (core/utils/auth.py RegisterUserCheck), so the two smoke e-mails must be dissimilar."""
    p = lambda s: ' '.join(sorted(re.sub(r'\W+', ' ', s.lower()).split()))
    a, b = p(a), p(b)
    return round(200 * _lcs(a, b) / (len(a) + len(b)))


def make_emails():
    while True:
        a = f'smoke-a-{rand_alnum(20)}@example.test'
        b = f'smoke-b-{rand_alnum(20)}@example.test'
        if similarity(a, b) < 70:
            return a, b


def jwt_user_id(token):
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get('user_id')
    except Exception:
        return None


def run_django_script(args, script, env):
    """Run one of our Django-shell scripts inside the backend container; returns the SMOKE_JSON payload."""
    code = open(os.path.join(HERE, script)).read()
    preamble = ('import json as _smoke_json, os as _smoke_os\n'
                f'_smoke_os.environ.update(_smoke_json.loads({json.dumps(json.dumps(env))}))\n')
    cmd = shlex.split(args.shell_cmd) + ['-c', preamble + code]
    log(f'    $ (cd {args.compose_dir} && {args.shell_cmd} -c "<{script}>")  env={env}')
    try:
        p = subprocess.run(cmd, cwd=args.compose_dir, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SmokeFailure(f'{script}: could not run Django shell: {e}')
    result = None
    for line in p.stdout.splitlines():
        if line.startswith('SMOKE_JSON:'):
            result = json.loads(line[len('SMOKE_JSON:'):])
        elif line.strip():
            log(f'    | {line}')
    if p.returncode != 0 or result is None:
        raise SmokeFailure(f'{script} failed (rc={p.returncode}).\nstdout:\n{p.stdout[-3000:]}\nstderr:\n{p.stderr[-3000:]}')
    return result


# ---------------------------------------------------------------- steps
def register_api(api, user, country):
    payload = {
        'username': user['email'], 'email': user['email'],
        'password1': user['password'], 'password2': user['password'],
        'first_name': 'Smoke', 'last_name': user['label'],
        'country': country, 'lang': 'en',
        # Field is required (allow_blank). Ignored when CAPTCHA_ENABLED=False; with Google's test secret
        # any non-empty value validates (but that needs google.com reachable from the backend).
        'captchaResponse': os.environ.get('CAPTCHA_TOKEN', 'smoke-test-token'),
    }
    return api('POST', 'auth/registration/', payload, timeout=90)


def mailpit_code(mailpit, email, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = []
        st, data = http('GET', f'{mailpit}/api/v1/search?query=' + urllib.parse.quote(f'to:"{email}"') + '&limit=50')
        if st == 200 and isinstance(data, dict):
            msgs = data.get('messages') or []
        if not msgs:
            st, data = http('GET', f'{mailpit}/api/v1/messages?limit=200')
            msgs = (data or {}).get('messages') or [] if st == 200 else []
        msgs = [m for m in msgs if any((t.get('Address') or '').lower() == email for t in (m.get('To') or []))]
        msgs.sort(key=lambda m: 'confirm' not in (m.get('Subject') or '').lower())  # confirmation mails first
        for m in msgs:
            st, full = http('GET', f'{mailpit}/api/v1/message/{m["ID"]}')
            if st != 200 or not isinstance(full, dict):
                continue
            text = full.get('Text') or re.sub(r'<[^>]+>', ' ', full.get('HTML') or '')
            mt = re.search(r'^\s*(\d{6})\s*$', text, re.M) or re.search(r'\b(\d{6})\b', text)
            if mt:
                return mt.group(1), m.get('Subject')
        time.sleep(1.5)
    raise SmokeFailure(f'no confirmation e-mail with a 6-digit code for {email} in Mailpit after {timeout}s '
                       f'(check EMAIL_HOST/EMAIL_PORT point to mailpit:1025 and `docker compose logs opencex`)')


def get_balances(api, token, codes):
    st, data = api('GET', 'balance/', token=token)
    if st != 200 or not isinstance(data, dict) or not data.get('balance'):
        raise SmokeFailure(f'GET /balance/ -> {st} {jdump(data)[:500]} (empty balance => token not accepted)')
    b = data['balance']
    return {c: {'actual': q8(b.get(c, {}).get('actual', 0)), 'orders': q8(b.get(c, {}).get('orders', 0))} for c in codes}


def place_order(api, token, pair, operation, qty, price):
    payload = {'pair': pair, 'operation': operation, 'type': 0, 'quantity': str(qty), 'price': str(price)}
    st, data = api('POST', 'orders/', payload, token=token)
    if st not in (200, 201) or not isinstance(data, dict) or 'id' not in data:
        raise SmokeFailure(f'POST /orders/ {payload} -> {st} {jdump(data)[:800]}')
    return data


def get_order(api, token, oid):
    st, data = api('GET', f'orders/{oid}/', token=token)
    if st != 200:
        raise SmokeFailure(f'GET /orders/{oid}/ -> {st} {jdump(data)[:300]}')
    return data


def main():
    e = os.environ.get
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base-url', default=e('BASE_URL', 'http://localhost'))
    ap.add_argument('--mailpit-url', default=e('MAILPIT_URL', 'http://localhost:8025'))
    ap.add_argument('--compose-dir', default=e('COMPOSE_DIR', '/home/user/OpenCEX/smoke-test'))
    ap.add_argument('--service', default=e('SERVICE', 'opencex'))
    ap.add_argument('--shell-cmd', default=e('DJANGO_SHELL_CMD'))
    ap.add_argument('--pair', default=e('PAIR', 'BTC-USDT'))
    ap.add_argument('--price', default=e('PRICE', '30000'))
    ap.add_argument('--qty', default=e('QTY', '0.01'))
    ap.add_argument('--timeout', type=int, default=int(e('TIMEOUT', '60')))
    ap.add_argument('--country', default=e('COUNTRY', 'DE'))
    ap.add_argument('--credit-mode', choices=['docker', 'manual', 'skip'], default=e('CREDIT_MODE', 'docker'))
    ap.add_argument('--register-mode', choices=['auto', 'api', 'orm'], default=e('REGISTER_MODE', 'auto'))
    ap.add_argument('--allow-crossing', action='store_true', help='do not abort if foreign orders cross PRICE')
    args = ap.parse_args()
    args.shell_cmd = args.shell_cmd or f'docker compose exec -T {args.service} python manage.py shell'
    args.mailpit_url = args.mailpit_url.rstrip('/')

    api = Api(args.base_url)
    pair = args.pair.upper()
    base_cur, quote_cur = pair.split('-')
    price, qty = q8(args.price), q8(args.qty)
    cost = q8(price * qty)
    used_fallback = False
    placed = []  # (token, order_id) for cleanup on failure
    A = {'label': 'A'}
    B = {'label': 'B'}

    try:
        # ------------------------------------------------ preflight
        step(f'Preflight: {args.base_url} and {args.mailpit_url}')
        st, data = api('GET', 'pairs/')
        if st != 200:
            raise SmokeFailure(f'GET /api/v1/pairs/ -> {st} {jdump(data)[:400]} (400 => Host not in ALLOWED_HOSTS: '
                               'set DOMAIN=localhost or IS_TEST=True; 502 => backend down)')
        codes = [p.get('code') for p in data.get('pairs', [])]
        log(f'    enabled pairs: {codes}')
        if pair not in codes:
            raise SmokeFailure(f'{pair} not listed by /pairs/ => no enabled PairSettings row (run wizard.py or create it)')
        st, _ = http('GET', f'{args.mailpit_url}/api/v1/messages?limit=1')
        if st != 200:
            raise SmokeFailure(f'Mailpit API not reachable at {args.mailpit_url} ({st})')

        # ------------------------------------------------ register
        A['email'], B['email'] = make_emails()
        for u in (A, B):
            u['password'] = 'Sm0ke!' + secrets.token_urlsafe(12)
        step(f'Register A={A["email"]}  B={B["email"]}  (mode {args.register_mode})')
        pending = [A, B]
        if args.register_mode in ('auto', 'api'):
            for u in list(pending):
                st, data = register_api(api, u, args.country)
                if st == 201:
                    log(f'    {u["label"]}: 201 {jdump(data)}')
                    pending.remove(u)
                    continue
                captchaish = st == 0 or st >= 500 or 'captcha' in jdump(data).lower()
                log(f'    {u["label"]}: registration API -> {st} {jdump(data)[:600]}')
                if args.register_mode == 'api' or not captchaish:
                    raise SmokeFailure(f'registration of {u["email"]} failed: {st} {jdump(data)[:600]}')
                log('    WARN: looks like the reCAPTCHA check (calls google.com) -> falling back to ORM registration')
                break
        if pending:
            used_fallback = True
            users = [{'email': u['email'], 'password': u['password'], 'first_name': 'Smoke',
                      'last_name': u['label'], 'country': args.country} for u in pending]
            res = run_django_script(args, 'orm_register.py', {'SMOKE_USERS_JSON': json.dumps(users)})
            log(f'    orm_register: {res}')

        # ------------------------------------------------ confirm + login
        for u in (A, B):
            step(f'{u["label"]}: confirmation e-mail, verify, login')
            code, subject = mailpit_code(args.mailpit_url, u['email'])
            log(f'    Mailpit: "{subject}" -> code {code}')
            st, data = api('POST', 'auth/login/', {'username': u['email'], 'password': u['password']})
            if st == 200:
                log('    WARN: login succeeded BEFORE e-mail confirmation (expected email_not_verified)')
            elif 'email_not_verified' in jdump(data):
                log(f'    login before confirmation correctly blocked ({st} email_not_verified)')
            else:
                log(f'    WARN: login before confirmation -> {st} {jdump(data)[:300]}')
            st, data = api('POST', 'auth/registration/verify-email/', {'key': code})
            if st != 200:
                raise SmokeFailure(f'verify-email {code} -> {st} {jdump(data)[:300]}')
            log(f'    verify-email -> 200 {jdump(data)}')
            st, data = api('POST', 'auth/login/', {'username': u['email'], 'password': u['password']})
            if st != 200 or not (data or {}).get('access_token'):
                hint = ''
                if 'captcha' in jdump(data).lower():
                    hint = (' (captcha required: set CAPTCHA_ENABLED=False, or CAPTCHA_ALLOWED_IP_MASK must match '
                            'the client IP Django sees = docker gateway 172.x)')
                raise SmokeFailure(f'login {u["email"]} -> {st} {jdump(data)[:400]}{hint}')
            u['token'] = data['access_token']
            u['user_id'] = jwt_user_id(u['token'])
            st, prof = api('GET', 'profile/', token=u['token'])
            u['user_fee'] = ((prof or {}).get('user') or {}).get('user_fee') if st == 200 else None
            log(f'    login OK: user_id={u["user_id"]} (Bearer JWT), profile user_fee={u["user_fee"]}')

        log('\nUSERS: ' + jdump({u['label']: {'email': u['email'], 'user_id': u['user_id'], 'password': u['password']}
                                for u in (A, B)}))

        # ------------------------------------------------ credit
        step(f'Credit balances (mode {args.credit_mode})')
        emails = f'{A["email"]},{B["email"]}'
        credits = f'{base_cur}=1,{quote_cur}=100000'
        if args.credit_mode == 'docker':
            res = run_django_script(args, 'credit_balances.py', {'SMOKE_EMAILS': emails, 'SMOKE_CREDITS': credits})
            log(f'    credited: {jdump(res)}')
        elif args.credit_mode == 'manual':
            log(f'    Credit the users now, e.g.:\n    cd {args.compose_dir} && docker compose exec -T '
                f'-e SMOKE_EMAILS={emails} -e SMOKE_CREDITS={credits} {args.service} python manage.py shell '
                f'< {os.path.join(HERE, "credit_balances.py")}')
            if sys.stdin.isatty():
                input('    Press Enter when done... ')
        need = {'A': (base_cur, qty), 'B': (quote_cur, cost)}
        deadline = time.time() + (600 if args.credit_mode == 'manual' else 10)
        while True:
            ok = all(get_balances(api, u['token'], [need[u['label']][0]])[need[u['label']][0]]['actual']
                     >= need[u['label']][1] for u in (A, B))
            if ok:
                break
            if time.time() > deadline:
                raise SmokeFailure(f'insufficient funds: A needs {qty} {base_cur}, B needs {cost} {quote_cur}')
            time.sleep(2)

        # ------------------------------------------------ before
        step('Balances before')
        before = {u['label']: get_balances(api, u['token'], [base_cur, quote_cur]) for u in (A, B)}
        log('    ' + jdump(before))

        st, stack = api('GET', f'stack/{pair}/')
        stack = stack if st == 200 and isinstance(stack, dict) else {}
        if not stack:
            log('    WARN: order book cache empty (is opencex-stack / bin/stack.py running?)')
        crossing = [o for o in stack.get('sells', []) if D(o['price']) <= price] + \
                   [o for o in stack.get('buys', []) if D(o['price']) >= price]
        if crossing and not args.allow_crossing:
            raise SmokeFailure(f'foreign orders already cross {price} and would match first: {jdump(crossing)[:600]} '
                               '(cancel them, use another --price, or --allow-crossing)')

        # ------------------------------------------------ trade
        step(f'A: limit SELL {qty} {base_cur} @ {price} {quote_cur}')
        oa = place_order(api, A['token'], pair, 1, qty, price)
        placed.append((A['token'], oa['id']))
        log(f'    order {oa["id"]} created: state={ORDER_STATES.get(oa.get("state"))} {jdump(oa)}')
        t0 = time.time()  # give the stack worker a moment so A is the resting (maker) order
        while time.time() - t0 < 5:
            st, s = api('GET', f'stack/{pair}/')
            if st == 200 and any(o.get('id') == oa['id'] for o in (s or {}).get('sells', [])):
                log(f'    order {oa["id"]} visible in order book after {time.time() - t0:.1f}s')
                break
            time.sleep(0.5)

        step(f'B: limit BUY {qty} {base_cur} @ {price} {quote_cur}')
        ob = place_order(api, B['token'], pair, 0, qty, price)
        placed.append((B['token'], ob['id']))
        log(f'    order {ob["id"]} created: state={ORDER_STATES.get(ob.get("state"))}')

        step(f'Waiting up to {args.timeout}s for both orders to be filled (async matching in opencex-stack)')
        deadline = time.time() + args.timeout
        while True:
            fa, fb = get_order(api, A['token'], oa['id']), get_order(api, B['token'], ob['id'])
            done = all(o.get('state') == 1 and D(o.get('quantity_left')) == 0 for o in (fa, fb))
            if done:
                log(f'    filled after {args.timeout - (deadline - time.time()):.1f}s')
                break
            if time.time() > deadline:
                raise SmokeFailure(
                    f'orders not filled in {args.timeout}s: A#{fa["id"]} state={ORDER_STATES.get(fa.get("state"))} '
                    f'left={fa.get("quantity_left")}, B#{fb["id"]} state={ORDER_STATES.get(fb.get("state"))} '
                    f'left={fb.get("quantity_left")} -- is opencex-stack (bin/stack.py) consuming orders.{pair}? '
                    f'(it builds its queue list from core_pair at start-up)')
            time.sleep(1)
        placed.clear()
        for lbl, o in (('A', fa), ('B', fb)):
            log(f'    {lbl} order: ' + jdump({k: o.get(k) for k in
                                             ('id', 'state', 'operation', 'quantity', 'price', 'quantity_left', 'executed', 'vwap')}))

        st, trades = api('GET', 'recent_trades/?limit=20')
        rows = trades.get('results', trades) if isinstance(trades, dict) else (trades or [])
        hit = [t for t in rows if isinstance(t, dict) and t.get('pair') == pair and q8(t.get('price')) == price
               and q8(t.get('quantity')) == qty]
        log(f'    GET /recent_trades/ -> {st}; matching trade row: {jdump(hit[:1]) if hit else "NOT FOUND (warn only)"}')

        # ------------------------------------------------ after + assertions
        time.sleep(0.5)
        step('Balances after')
        after = {u['label']: get_balances(api, u['token'], [base_cur, quote_cur]) for u in (A, B)}
        log('    ' + jdump(after))

        # Fee model (core/models/orders/__init__.py Order._execute/transaction/calculate_fee_amount):
        # each side pays its fee out of what it RECEIVES; rate = UserFee.fee_rate if set, else
        # FeesAndLimits.fee_order_limits of the received currency (BUY -> base, SELL -> quote); min fee 1e-8.
        st, limits = api('GET', 'limits/')
        limits = limits if st == 200 and isinstance(limits, dict) else {}

        def rate(user, cur):
            if user.get('user_fee') is not None:
                return D(user['user_fee'])
            return D((((limits.get(cur) or {}).get('fee') or {}).get('order') or {}).get('limit', 0))

        def fee(amount, r):
            if r == 0:
                return Decimal(0)
            return max(q8(amount * r), Q8)

        rate_a, rate_b = rate(A, quote_cur), rate(B, base_cur)
        fee_a, fee_b = fee(cost, rate_a), fee(qty, rate_b)
        expected = {
            ('A', base_cur): -qty, ('A', quote_cur): q8(cost - fee_a),
            ('B', base_cur): q8(qty - fee_b), ('B', quote_cur): -cost,
        }
        failures = []
        log(f'\n    fee rates: A(seller, pays in {quote_cur})={rate_a}  B(buyer, pays in {base_cur})={rate_b}')
        log(f'    {"user":4} {"cur":5} {"before":>18} {"after":>18} {"delta":>16} {"expected":>16}  orders(b->a)')
        for (lbl, cur), exp in expected.items():
            b, a = before[lbl][cur], after[lbl][cur]
            delta = a['actual'] - b['actual']
            ok = abs(delta - exp) <= TOL and abs(a['orders'] - b['orders']) <= TOL
            if not ok:
                failures.append(f'{lbl} {cur}: delta {fmt(delta)} expected {fmt(exp)}; '
                                f'in-orders {fmt(b["orders"])}->{fmt(a["orders"])}')
            log(f'    {lbl:4} {cur:5} {fmt(b["actual"]):>18} {fmt(a["actual"]):>18} {fmt(delta):>16} {fmt(exp):>16}'
                f'  {fmt(b["orders"])}->{fmt(a["orders"])}  {"OK" if ok else "MISMATCH"}')
        log(f'    exchange fee collected: {fmt(fee_a)} {quote_cur} (from A) + {fmt(fee_b)} {base_cur} (from B)')
        if failures:
            raise SmokeFailure('balance assertions failed:\n  - ' + '\n  - '.join(failures))

    except SmokeFailure as exc:
        for token, oid in placed:  # best-effort cleanup so the next run's book is clean
            st, _ = api('DELETE', f'orders/{oid}/', token=token)
            log(f'    cleanup: cancel order {oid} -> {st}')
        log(f'\nRESULT: FAIL\n{exc}')
        return 1

    if used_fallback:
        log('\nRESULT: PASS (trade + balances), but registration API was blocked -> users created via ORM fallback')
        return 2
    log('\nRESULT: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())

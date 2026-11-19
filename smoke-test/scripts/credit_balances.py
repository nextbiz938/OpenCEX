# Credit TEST balances to OpenCEX users the ledger-consistent way.
# Pipe into the Django shell (or pass as -c):
#   docker compose exec -T -e SMOKE_EMAILS=a@example.test,b@example.test opencex python manage.py shell < scripts/credit_balances.py
#
# Mirrors wizard.py:516-519 and the admin "topup" action (admin_rest/admin_rest.py:578-591):
#   Transaction.topup(..., reason=REASON_MANUAL_TOPUP) -> Transaction.save() -> update_balance()
#   -> BalanceManager.increase_amount() (creates/updates core_balance), then a WalletHistoryItem.
# Balance rows are never written directly.
#
# Env:
#   SMOKE_EMAILS         comma-separated usernames/emails (required)
#   SMOKE_CREDITS        default "BTC=1,USDT=100000"
#   SMOKE_EMAIL_DOMAIN   safety guard: only users whose email ends with "@<domain>" are credited (default example.test)
#   SMOKE_ALLOW_ANY_EMAIL=1 disables that guard
# Last stdout line: "SMOKE_JSON:{...}" (machine-readable result for smoke_trade.py).
import json as _sj
import os as _so
from decimal import Decimal as _SD

from django.contrib.auth import get_user_model as _get_user_model
from django.db.transaction import atomic as _atomic

from core.currency import Currency as _Currency
from core.models import Transaction as _Transaction
from core.models.inouts.balance import Balance as _Balance
from core.models.inouts.transaction import REASON_MANUAL_TOPUP as _REASON_MANUAL_TOPUP
from core.utils.wallet_history import create_or_update_wallet_history_item_from_transaction as _wh


def _smoke_credit():
    User = _get_user_model()
    emails = [e.strip().lower() for e in _so.environ.get('SMOKE_EMAILS', '').split(',') if e.strip()]
    if not emails:
        raise SystemExit('SMOKE_EMAILS is empty')
    credits = []
    for part in _so.environ.get('SMOKE_CREDITS', 'BTC=1,USDT=100000').split(','):
        code, amount = part.split('=')
        credits.append((_Currency.get(code.strip()), _SD(amount.strip())))
    domain = _so.environ.get('SMOKE_EMAIL_DOMAIN', 'example.test').lower()
    allow_any = _so.environ.get('SMOKE_ALLOW_ANY_EMAIL') == '1'

    result = {}
    for email in emails:
        if not allow_any and not email.endswith('@' + domain):
            raise SystemExit(f'refusing to credit {email}: not @{domain} (set SMOKE_ALLOW_ANY_EMAIL=1)')
        user = User.objects.get(username=email)
        txs = []
        with _atomic():
            for currency, amount in credits:
                tx = _Transaction.topup(user.id, currency, amount, {'1': 1, 'source': 'smoke-test'},
                                        reason=_REASON_MANUAL_TOPUP)
                _wh(tx)
                txs.append({'tx_id': tx.id, 'currency': currency.code, 'amount': str(amount)})
        balances = {}
        for currency, _ in credits:
            b = _Balance.for_user(user, currency)
            balances[currency.code] = {'actual': str(b['actual']), 'orders': str(b['orders'])}
        result[email] = {'user_id': user.id, 'transactions': txs, 'balances': balances}
        print(f'credited {email} (id {user.id}): {txs} -> {balances}')
    print('SMOKE_JSON:' + _sj.dumps(result))


_smoke_credit()

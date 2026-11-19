# Pipe into `python manage.py shell`. Creates verified demo users and credits test balances,
# so you can log in and trade in the browser right away.
#   DEMO_USERS="alice@example.test:password1,bob@example.test:password2"
#   DEMO_CREDITS="BTC=1,USDT=100000"   (only credited when the user is first created)
import os as _os


def _demo_users():
    from allauth.account.models import EmailAddress
    from django.contrib.auth import get_user_model
    from core.currency import Currency
    from core.models import Transaction
    from core.models.inouts.transaction import REASON_MANUAL_TOPUP
    from core.utils.wallet_history import create_or_update_wallet_history_item_from_transaction

    User = get_user_model()
    credits = []
    for part in _os.environ.get('DEMO_CREDITS', 'BTC=1,USDT=100000').split(','):
        code, amount = part.split('=')
        credits.append((code.strip(), amount.strip()))

    for entry in _os.environ['DEMO_USERS'].split(','):
        email, password = entry.split(':', 1)
        email = email.strip().lower()
        if not email.endswith('@example.test'):
            raise SystemExit(f'refusing to create non-test user {email}')
        user = User.objects.filter(username=email).first()
        if user:
            print(f'exists  {email} (balances untouched)')
            continue
        user = User.objects.create_user(email, email, password, first_name='Demo', last_name='User')
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        for code, amount in credits:
            tx = Transaction.topup(user.id, Currency.get(code), amount, {'1': 1}, reason=REASON_MANUAL_TOPUP)
            create_or_update_wallet_history_item_from_transaction(tx)
        print(f'created {email} with ' + ', '.join(f'{a} {c}' for c, a in credits))


_demo_users()

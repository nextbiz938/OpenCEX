# FALLBACK ONLY: register users without the HTTP API (used by smoke_trade.py --register-mode auto|orm
# when POST /api/v1/auth/registration/ is blocked, e.g. by reCAPTCHA calling google.com).
# Mirrors what dj-rest-auth RegisterView + allauth do: create user (signals create Profile etc.),
# create an UNVERIFIED primary EmailAddress and send the real confirmation e-mail (6-digit key from
# core/auth/adapters.py:generate_emailconfirmation_key) through Django's SMTP backend -> Mailpit.
# Confirmation + login are then still done via the API.
#
# Env: SMOKE_USERS_JSON='[{"email":..,"password":..,"first_name":..,"last_name":..,"country":"DE"}]'
#      SMOKE_EMAIL_DOMAIN (guard, default example.test)
import json as _rj
import os as _ro

from allauth.account.models import EmailAddress as _EmailAddress
from django.contrib.auth import get_user_model as _rget_user_model
from django.db.transaction import atomic as _ratomic

from core.utils.auth import RegisterUserCheck as _RegisterUserCheck


def _smoke_register():
    User = _rget_user_model()
    domain = _ro.environ.get('SMOKE_EMAIL_DOMAIN', 'example.test').lower()
    out = {}
    for u in _rj.loads(_ro.environ['SMOKE_USERS_JSON']):
        email = u['email'].strip().lower()
        if not email.endswith('@' + domain):
            raise SystemExit(f'refusing to register {email}: not @{domain}')
        user = User.objects.filter(username=email).first()
        created = user is None
        if created:
            with _ratomic():
                user = User.objects.create_user(username=email, email=email, password=u['password'],
                                                first_name=u.get('first_name', 'Smoke'),
                                                last_name=u.get('last_name', 'Test'))
                user.profile.country = u.get('country', 'DE')
                user.profile.save()
        ea, _ = _EmailAddress.objects.get_or_create(user=user, email=email,
                                                    defaults={'primary': True, 'verified': False})
        sent = False
        if not ea.verified:
            ea.send_confirmation(request=None, signup=True)
            sent = True
        out[email] = {'user_id': user.id, 'created': created, 'confirmation_sent': sent}
    _RegisterUserCheck.update_last_emails()
    print('SMOKE_JSON:' + _rj.dumps(out))


_smoke_register()

10-public-home.jpg | Public home page | The Nuxt marketing site at `http://localhost/`, with the Menu open (Wallet, Exchange, Quick Swap, Fees). The BTC price comes from the exchange's own last trade.
11-public-home-full.jpg | Public home page (full) | The whole landing page. It loads Tailwind CSS from a CDN; the test VM is offline, so these screenshots use a locally built copy (it looks the same with internet).
12-login.jpg | Sign in | The exchange app's login page (`/account/login`). Email first, then password.
13-register-empty.jpg | Sign up | Registration form: name, email, date of birth, password rules, country and terms checkbox. Captcha is switched off in this test install (Google is unreachable from the VM).
14-register-filled.jpg | Sign up, filled in | A new test user `grace.…@example.test`. The password checklist turns green as the rules are met; US is not in the allowed country list.
15-register-enter-code.jpg | Confirm email | After "Create account" the app asks for the 6-digit code it just emailed.
16-mailpit-inbox.jpg | Test inbox (Mailpit) | All emails go to the local Mailpit at `http://localhost:8025` instead of a real mail server.
17-mailpit-confirmation-code.jpg | Confirmation email | The "[OpenCEXSmoke] Email Confirmation" email with the code.
18-code-entered.jpg | Code entered | The code typed into the confirm screen.
19-email-confirmed.jpg | Registered | "Account successfully registered", then the login page.
20-login-filled.jpg | Sign in, filled in | Logging in as the new user (password masked).
21-logged-in.jpg | First login: choose interface | New users pick the Simple or Advanced interface (changeable later).
22-settings.jpg | Account settings | 2FA (off by default), auto-logout, default interface, IP-change and login-failure notifications, password change and personal info.
23-fees.jpg | Fees & limits | Trading fee levels (0.1% maker / 0.1% taker) and deposit/withdrawal fees and limits per coin, as set up by the installer wizard.
24-support.jpg | Customer support | The support page.
25-kyc.jpg | KYC | Blank apart from a Back button: KYC (Sumsub) is switched off in this test install.
26-mobile-home.jpg | Mobile: home | Public site on an iPhone 13 sized screen.
27-mobile-trade.jpg | Mobile: trading | The BTC-USDT trading page on mobile.
28-mobile-wallet.jpg | Mobile: wallet | The wallet on mobile.

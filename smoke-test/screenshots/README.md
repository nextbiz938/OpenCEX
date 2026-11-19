# OpenCEX test install: screenshot tour

Captured from the smoke-test stack (`smoke-test/setup.sh`) on a throwaway VM. Play money only; no blockchain nodes and no internet inside the containers, so anything that needs a real chain or a price feed is shown failing honestly.

- [Public site, sign-up and sign-in](#public-site-sign-up-and-sign-in)
- [Wallet, deposits and withdrawals](#wallet-deposits-and-withdrawals)
- [Trading and charts](#trading-and-charts)
- [Operator side: admin panel, queues, mail](#operator-side-admin-panel-queues-mail)

## Public site, sign-up and sign-in

### Public home page

The Nuxt marketing site at `http://localhost/`, with the Menu open (Wallet, Exchange, Quick Swap, Fees). The BTC price comes from the exchange's own last trade.

![Public home page](10-public-home.jpg)

### Public home page (full)

The whole landing page. It loads Tailwind CSS from a CDN; the test VM is offline, so these screenshots use a locally built copy (it looks the same with internet).

![Public home page (full)](11-public-home-full.jpg)

### Sign in

The exchange app's login page (`/account/login`). Email first, then password.

![Sign in](12-login.jpg)

### Sign up

Registration form: name, email, date of birth, password rules, country and terms checkbox. Captcha is switched off in this test install (Google is unreachable from the VM).

![Sign up](13-register-empty.jpg)

### Sign up, filled in

A new test user `grace.…@example.test`. The password checklist turns green as the rules are met; US is not in the allowed country list.

![Sign up, filled in](14-register-filled.jpg)

### Confirm email

After "Create account" the app asks for the 6-digit code it just emailed.

![Confirm email](15-register-enter-code.jpg)

### Test inbox (Mailpit)

All emails go to the local Mailpit at `http://localhost:8025` instead of a real mail server.

![Test inbox (Mailpit)](16-mailpit-inbox.jpg)

### Confirmation email

The "[OpenCEXSmoke] Email Confirmation" email with the code.

![Confirmation email](17-mailpit-confirmation-code.jpg)

### Code entered

The code typed into the confirm screen.

![Code entered](18-code-entered.jpg)

### Registered

"Account successfully registered", then the login page.

![Registered](19-email-confirmed.jpg)

### Sign in, filled in

Logging in as the new user (password masked).

![Sign in, filled in](20-login-filled.jpg)

### First login: choose interface

New users pick the Simple or Advanced interface (changeable later).

![First login: choose interface](21-logged-in.jpg)

### Account settings

2FA (off by default), auto-logout, default interface, IP-change and login-failure notifications, password change and personal info.

![Account settings](22-settings.jpg)

### Fees & limits

Trading fee levels (0.1% maker / 0.1% taker) and deposit/withdrawal fees and limits per coin, as set up by the installer wizard.

![Fees & limits](23-fees.jpg)

### Customer support

The support page.

![Customer support](24-support.jpg)

### KYC

Blank apart from a Back button: KYC (Sumsub) is switched off in this test install.

![KYC](25-kyc.jpg)

### Mobile: home

Public site on an iPhone 13 sized screen.

![Mobile: home](26-mobile-home.jpg)

### Mobile: trading

The BTC-USDT trading page on mobile.

![Mobile: trading](27-mobile-trade.jpg)

### Mobile: wallet

The wallet on mobile.

![Mobile: wallet](28-mobile-wallet.jpg)

## Wallet, deposits and withdrawals

### Wallet (empty)

A fresh user (erin) with zero balances. Each coin has Deposit, Withdrawal and History actions.

![Wallet (empty)](30-wallet-empty.jpg)

### Wallet (funded)

Demo user dave with 1 BTC and 100,000 USDT of play money.

![Wallet (funded)](31-wallet-funded.jpg)

### Deposit BTC

Deposit page: pick coin and network, then "Create" a deposit address.

![Deposit BTC](32-deposit-btc.jpg)

### Deposit BTC: needs a node

Creating a BTC address just spins: BTC addresses come from the bitcoin node, and there is none in this test (bitcoind was skipped).

![Deposit BTC: needs a node](33-deposit-btc-create-address.jpg)

### Deposit ETH

Same page for Ethereum.

![Deposit ETH](34-deposit-eth.jpg)

### Deposit ETH: address + QR

ETH addresses are generated offline, so this works: address, QR code, min/max deposit and fee. Nothing would arrive, since no ETH node/scanner is running.

![Deposit ETH: address + QR](35-deposit-eth-create-address.jpg)

### Deposit USDT

USDT with the network selector (ERC-20 on Ethereum here; TRC-20/BEP-20 are disabled).

![Deposit USDT](36-deposit-usdt.jpg)

### Deposit USDT: address + QR

ERC-20 USDT deposit address, with the warning to deposit only from the ERC-20 network.

![Deposit USDT: address + QR](37-deposit-usdt-create-address.jpg)

### TEST deposit, step 1: admin

Real deposits need a blockchain, so a test deposit is done the operator's way: Admin panel → Users → erin → Action menu (Confirm email, Make Topup, Drop 2FA, Drop SMS).

![TEST deposit, step 1: admin](38-admin-user-actions.jpg)

### TEST deposit, step 2: Make Topup

Tick the user, click MAKE TOPUP, enter amount and currency. The admin must also type the Master Pass (left blank in this screenshot).

![TEST deposit, step 2: Make Topup](39-admin-topup-dialog.jpg)

### TEST deposit, step 3: done

After DO the topup is applied (0.5 BTC, then 5,000 USDT). This only worked after fixing the nginx `X-Forwarded-Proto` bug (see REPORT.md); before that, every admin action button silently did nothing over plain http.

![TEST deposit, step 3: done](40-admin-topup-done.jpg)

### Wallet after test deposit

erin now has 0.5 BTC and 5,000 USDT, listed as "Deposit / Done" under Recent Transactions.

![Wallet after test deposit](41-wallet-after-test-deposit.jpg)

### Deposit history

The BTC history page with the credited deposit.

![Deposit history](42-wallet-history-deposits.jpg)

### Withdrawal form

Withdraw page: available balance, balance after withdrawal, amount, destination address, min/max, fee and receive amount.

![Withdrawal form](43-withdrawal-form.jpg)

### Withdraw BTC (test address)

0.01 BTC to a public testnet test-vector address.

![Withdraw BTC (test address)](44-withdrawal-btc-filled.jpg)

### Withdraw BTC: fails silently

Nothing visible happens. The API returned **500**: the limit check multiplies by the external BTC price, which is `None` with no price feed (`TypeError: Decimal * NoneType`, `core/serializers/withdrawal.py:112`). Upstream bug: non-USDT withdrawals crash whenever the price feed is down.

![Withdraw BTC: fails silently](45-withdrawal-btc-submitted.jpg)

### Withdraw USDT (test address)

20 USDT to Anvil/Hardhat's public test account #0. New users can withdraw up to 100 USDT per month (limit level 0); 250 USDT was refused with "Out of limit!".

![Withdraw USDT (test address)](46-withdrawal-usdt-filled.jpg)

### Withdrawal: enter emailed code

After submit, the app emails a code and shows the confirm box. The request appears as "Waiting for confirmation".

![Withdrawal: enter emailed code](47-withdrawal-usdt-submitted.jpg)

### Withdrawal confirmation email

The "Withdrawal request confirmation" email in Mailpit, with a 6-digit code.

![Withdrawal confirmation email](48-withdrawal-confirm-email.jpg)

### Code entered

The code typed in, ready to confirm.

![Code entered](49-withdrawal-code-entered.jpg)

### Withdrawal confirmed

"Success! Withdrawal request is in processing". It moves to "To be sent".

![Withdrawal confirmed](50-withdrawal-confirmed.jpg)

### Withdrawal in history

USDT history: the confirmed withdrawal ("To be sent") and an earlier unconfirmed one.

![Withdrawal in history](51-withdrawal-in-history.jpg)

### Admin: withdrawal requests

The operator queue: confirmed by the user but **not approved**. Approving would hand it to the payout worker, which needs a real ETH node and a funded hot wallet, so it was left alone.

![Admin: withdrawal requests](52-admin-withdrawal-requests.jpg)

## Trading and charts

### Trading page (BTC-USDT)

The Advanced interface, logged in as demo trader alice: order book (bids from bob, asks from alice), TradingView candle chart, Buy/Sell forms, market list and wallet.

![Trading page (BTC-USDT)](60-trade-page.jpg)

### Trading page (full)

The whole page including the lower panels (open orders, order history, trade history).

![Trading page (full)](61-trade-page-full.jpg)

### Chart

TradingView chart built from the test trades (alice and bob trading at a drifting price, roughly 29,500 to 31,500).

![Chart](62-chart-closeup.jpg)

### Chart: 1-hour candles

The same chart switched to a longer timeframe.

![Chart: 1-hour candles](63-chart-1h.jpg)

### Place a limit buy

Buy 0.015 BTC at 29,000 USDT: the form shows what you get, what you pay and the fee.

![Place a limit buy](64-buy-limit-filled.jpg)

### Order placed

The order is accepted and rests in the book below the best bid.

![Order placed](65-buy-limit-placed.jpg)

### Open orders

The new order in "Open orders" at the bottom of the page.

![Open orders](66-open-orders.jpg)

### Cancel an order

Red ✕ in Open Orders → "Order cancelled". The 29,000 buy disappears and its held USDT goes back to available balance.

![Cancel an order](67-order-cancelled.jpg)

### Edit an order

The ✎ button opens an in-place edit dialog (here for a stop-limit order: stop price, limit price, quantity).

![Edit an order](67b-edit-order-dialog.jpg)

### Sell into the best bid

Sell 0.01 BTC at 29,950, which crosses bob's best bid.

![Sell into the best bid](68-sell-into-bid-filled.jpg)

### Trade executed

The matching engine fills it within a second; balances update live.

![Trade executed](69-sell-executed.jpg)

### Trade history

The executed trade in the history panels.

![Trade history](70-trade-history.jpg)

### Stop-limit order

The stop-limit tab: a limit order that only activates when the stop price is reached.

![Stop-limit order](71-stop-limit-form.jpg)

### Stop-limit order placed

Accepted ("Order opened"): buy 0.01 BTC at 31,600 once the price reaches 31,500. It waits off-book until triggered.

![Stop-limit order placed](71b-stop-limit-placed.jpg)

### Dark theme

The trading page in the dark theme (toggle in the header).

![Dark theme](72-trade-page-dark.jpg)

### Wallet, dark theme

The wallet in the dark theme.

![Wallet, dark theme](73-wallet-dark.jpg)

### Quick Swap (Simple interface)

Instant exchange at the current book price (1 BTC = 29,900 USDT here). The Exchanger and Fast buy/sell links lead to this same page.

![Quick Swap (Simple interface)](74-quick-swap.jpg)

### ETH-USDT pair

ETH-USDT is enabled but has no price: no external feed and no trades yet, so orders here would be refused until an operator sets a custom price.

![ETH-USDT pair](77-eth-usdt-pair.jpg)

## Operator side: admin panel, queues, mail

### Admin panel login

`http://localhost/admin/`: email, password and a 2FA code. The installer wizard creates the admin with a TOTP device, so the code comes from an authenticator app.

![Admin panel login](80-admin-login.jpg)

### Admin dashboard

Operator overview after the test activity: latest topups, withdrawals, users and trading stats.

![Admin dashboard](81-admin-dashboard.jpg)

### Admin dashboard (full)

The whole dashboard page.

![Admin dashboard (full)](82-admin-dashboard-full.jpg)

### Users

All exchange users with staff/KYC/2FA flags, withdrawals and orders count, email-verified status, and per-user Action / view / edit / delete.

![Users](83-admin-users.jpg)

### User detail

One user (alice) opened from the list.

![User detail](84-admin-user-detail.jpg)

### All orders (no bots)

Every user order on the exchange: the test trades between alice and bob.

![All orders (no bots)](85-admin-orders.jpg)

### Matches

Executed trades (order matches) with price, quantity and fees.

![Matches](86-admin-matches.jpg)

### Balances

Per-user balances across all coins.

![Balances](87-admin-balances.jpg)

### Transactions

The ledger: manual topups, order holds/releases, trade settlements, withdrawals.

![Transactions](88-admin-transactions.jpg)

### Pair settings

Per-pair settings. BTC-USDT uses a **Custom** price of 30000 (set by the smoke test because the external price feed is unreachable); others are "External". Deviation 0.99 = orders may be up to 99% away from the reference price.

![Pair settings](89-admin-pair-settings.jpg)

### Coins management

Per-coin switches (topups, withdrawals, exchange, pairs, stack). TRX, BNB and MATIC are disabled, as chosen in the installer.

![Coins management](90-admin-coins-management.jpg)

### Fees and limits

Per-coin deposit/withdrawal/order limits and fees (values from the installer wizard).

![Fees and limits](91-admin-fees-and-limits.jpg)

### Withdrawal fees

Per-coin, per-network withdrawal fee.

![Withdrawal fees](92-admin-withdrawal-fee.jpg)

### Market-maker bots

The wizard's built-in bots per pair. They stay idle here: they need an external price ("External price unavailable"), and bot orders use a separate book that never matches user orders.

![Market-maker bots](93-admin-bot-configs.jpg)

### Bot detail

BTC-USDT bot settings: strategy, periods, order sizes, precision.

![Bot detail](94-admin-bot-detail.jpg)

### Coin info

Names, decimals, explorer links and logos shown in the UI.

![Coin info](95-admin-coin-info.jpg)

### All test emails

Every email the tour generated (sign-up and withdrawal codes), caught by Mailpit.

![All test emails](96-mailpit-all-mail.jpg)

### RabbitMQ overview

The message broker behind Celery (`http://localhost:15672`).

![RabbitMQ overview](97-rabbitmq-overview.jpg)

### RabbitMQ queues

One queue per job type, including the matching engine's `orders.BTC-USDT`. `eth_new_blocks` piles up unconsumed because the ETH block scanner is deliberately not running in this test.

![RabbitMQ queues](98-rabbitmq-queues.jpg)

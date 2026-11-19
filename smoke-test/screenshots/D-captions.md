80-admin-login.jpg | Admin panel login | `http://localhost/admin/`: email, password and a 2FA code. The installer wizard creates the admin with a TOTP device, so the code comes from an authenticator app.
81-admin-dashboard.jpg | Admin dashboard | Operator overview after the test activity: latest topups, withdrawals, users and trading stats.
82-admin-dashboard-full.jpg | Admin dashboard (full) | The whole dashboard page.
83-admin-users.jpg | Users | All exchange users with staff/KYC/2FA flags, withdrawals and orders count, email-verified status, and per-user Action / view / edit / delete.
84-admin-user-detail.jpg | User detail | One user (alice) opened from the list.
85-admin-orders.jpg | All orders (no bots) | Every user order on the exchange: the test trades between alice and bob.
86-admin-matches.jpg | Matches | Executed trades (order matches) with price, quantity and fees.
87-admin-balances.jpg | Balances | Per-user balances across all coins.
88-admin-transactions.jpg | Transactions | The ledger: manual topups, order holds/releases, trade settlements, withdrawals.
89-admin-pair-settings.jpg | Pair settings | Per-pair settings. BTC-USDT uses a **Custom** price of 30000 (set by the smoke test because the external price feed is unreachable); others are "External". Deviation 0.99 = orders may be up to 99% away from the reference price.
90-admin-coins-management.jpg | Coins management | Per-coin switches (topups, withdrawals, exchange, pairs, stack). TRX, BNB and MATIC are disabled, as chosen in the installer.
91-admin-fees-and-limits.jpg | Fees and limits | Per-coin deposit/withdrawal/order limits and fees (values from the installer wizard).
92-admin-withdrawal-fee.jpg | Withdrawal fees | Per-coin, per-network withdrawal fee.
93-admin-bot-configs.jpg | Market-maker bots | The wizard's built-in bots per pair. They stay idle here: they need an external price ("External price unavailable"), and bot orders use a separate book that never matches user orders.
94-admin-bot-detail.jpg | Bot detail | BTC-USDT bot settings: strategy, periods, order sizes, precision.
95-admin-coin-info.jpg | Coin info | Names, decimals, explorer links and logos shown in the UI.
96-mailpit-all-mail.jpg | All test emails | Every email the tour generated (sign-up and withdrawal codes), caught by Mailpit.
97-rabbitmq-overview.jpg | RabbitMQ overview | The message broker behind Celery (`http://localhost:15672`).
98-rabbitmq-queues.jpg | RabbitMQ queues | One queue per job type, including the matching engine's `orders.BTC-USDT`. `eth_new_blocks` piles up unconsumed because the ETH block scanner is deliberately not running in this test.

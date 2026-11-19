30-wallet-empty.jpg | Wallet (empty) | A fresh user (erin) with zero balances. Each coin has Deposit, Withdrawal and History actions.
31-wallet-funded.jpg | Wallet (funded) | Demo user dave with 1 BTC and 100,000 USDT of play money.
32-deposit-btc.jpg | Deposit BTC | Deposit page: pick coin and network, then "Create" a deposit address.
33-deposit-btc-create-address.jpg | Deposit BTC: needs a node | Creating a BTC address just spins: BTC addresses come from the bitcoin node, and there is none in this test (bitcoind was skipped).
34-deposit-eth.jpg | Deposit ETH | Same page for Ethereum.
35-deposit-eth-create-address.jpg | Deposit ETH: address + QR | ETH addresses are generated offline, so this works: address, QR code, min/max deposit and fee. Nothing would arrive, since no ETH node/scanner is running.
36-deposit-usdt.jpg | Deposit USDT | USDT with the network selector (ERC-20 on Ethereum here; TRC-20/BEP-20 are disabled).
37-deposit-usdt-create-address.jpg | Deposit USDT: address + QR | ERC-20 USDT deposit address, with the warning to deposit only from the ERC-20 network.
38-admin-user-actions.jpg | TEST deposit, step 1: admin | Real deposits need a blockchain, so a test deposit is done the operator's way: Admin panel → Users → erin → Action menu (Confirm email, Make Topup, Drop 2FA, Drop SMS).
39-admin-topup-dialog.jpg | TEST deposit, step 2: Make Topup | Tick the user, click MAKE TOPUP, enter amount and currency. The admin must also type the Master Pass (left blank in this screenshot).
40-admin-topup-done.jpg | TEST deposit, step 3: done | After DO the topup is applied (0.5 BTC, then 5,000 USDT). This only worked after fixing the nginx `X-Forwarded-Proto` bug (see REPORT.md); before that, every admin action button silently did nothing over plain http.
41-wallet-after-test-deposit.jpg | Wallet after test deposit | erin now has 0.5 BTC and 5,000 USDT, listed as "Deposit / Done" under Recent Transactions.
42-wallet-history-deposits.jpg | Deposit history | The BTC history page with the credited deposit.
43-withdrawal-form.jpg | Withdrawal form | Withdraw page: available balance, balance after withdrawal, amount, destination address, min/max, fee and receive amount.
44-withdrawal-btc-filled.jpg | Withdraw BTC (test address) | 0.01 BTC to a public testnet test-vector address.
45-withdrawal-btc-submitted.jpg | Withdraw BTC: fails silently | Nothing visible happens. The API returned **500**: the limit check multiplies by the external BTC price, which is `None` with no price feed (`TypeError: Decimal * NoneType`, `core/serializers/withdrawal.py:112`). Upstream bug: non-USDT withdrawals crash whenever the price feed is down.
46-withdrawal-usdt-filled.jpg | Withdraw USDT (test address) | 20 USDT to Anvil/Hardhat's public test account #0. New users can withdraw up to 100 USDT per month (limit level 0); 250 USDT was refused with "Out of limit!".
47-withdrawal-usdt-submitted.jpg | Withdrawal: enter emailed code | After submit, the app emails a code and shows the confirm box. The request appears as "Waiting for confirmation".
48-withdrawal-confirm-email.jpg | Withdrawal confirmation email | The "Withdrawal request confirmation" email in Mailpit, with a 6-digit code.
49-withdrawal-code-entered.jpg | Code entered | The code typed in, ready to confirm.
50-withdrawal-confirmed.jpg | Withdrawal confirmed | "Success! Withdrawal request is in processing". It moves to "To be sent".
51-withdrawal-in-history.jpg | Withdrawal in history | USDT history: the confirmed withdrawal ("To be sent") and an earlier unconfirmed one.
52-admin-withdrawal-requests.jpg | Admin: withdrawal requests | The operator queue: confirmed by the user but **not approved**. Approving would hand it to the payout worker, which needs a real ETH node and a funded hot wallet, so it was left alone.

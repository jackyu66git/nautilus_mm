# Testnet Limitations — MM_EDGE_EXP_001

Observed on **Binance USDT-M Futures Testnet** during Data Collection (Aug 2026).

## userTrades history cutoff

```
Endpoint:   GET /fapi/v1/userTrades
Observed max trade time (UTC): 2026-08-17T03:08:23
Behavior:   Pagination returns 3890 rows; no further trades via time/fromId
            after cutoff, even while probe continues to produce fills until
            2026-08-18.
```

**Impact:** Local jsonl fill count can exceed paginated `userTrades` count.
This is **not** evidence of duplicate local logging or fake fills.

## Order API remains available

```
Endpoint:   GET /fapi/v1/order?orderId=
Behavior:   Post-cutoff orders return status=FILLED, executedQty, avgPrice
            while userTrades?orderId= returns 0 rows for the same orderId.
```

RECON-03 classifies these as:

```
VENUE_CONFIRMED_NO_TRADE_HISTORY
```

Evidence grade: **Order only** (not dual Order+Trade).

## Income ledger continues

`GET /fapi/v1/income` continues to record COMMISSION / REALIZED_PNL after
the userTrades cutoff. Account reconciliation (RECON-01) uses income, not
userTrades alone.

## Implications for future runs

1. **Real-time immutable ledger** — persist on every `OrderFilled`:
   `venue_trade_id`, `venue_order_id`, `liquidity_side`, `commission`,
   `exchange_ts`, `local_ts`. Do not rely on post-hoc userTrades backfill.

2. **Reports must use evidence taxonomy** — never compare raw fill count to
   userTrades count without cutoff annotation.

3. **Strict trade-level closure** may remain FAIL on Testnet while
   **order-level closure** can still PASS.

## Maker-only constraint

Post-only orders rejected with `-5022` when they would take. Verified:
`TAKER_FILLED_COUNT = 0` on all 3890 trades inside userTrades window.

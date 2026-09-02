# synthetic_failed_payments.csv — Data Dictionary

⚠️ **This dataset is entirely SYNTHETIC** — generated with a fixed random seed (42) for reproducibility. No real user, payment, or transaction data is used anywhere in this file. Built to reflect realistic patterns based on Razorpay's publicly documented failure-reason categories and this project's own churn-scoring design.

**55 records** (exceeds the track's 50+ minimum), evenly spread across all 8 root causes.

## Fields

| Field | Type | Description |
|---|---|---|
| `payment_id` | string | Unique ID for this failed payment attempt |
| `user_id` | string | Unique customer ID (synthetic, reused across some records to simulate repeat failures) |
| `subscription_plan` | string | Basic (₹199) / Standard (₹499) / Premium (₹799) |
| `amount_inr` | number | Amount that failed to be charged |
| `failure_timestamp` | datetime | When the failure occurred — deliberately includes some odd-hour (11pm–7am) timestamps to exercise the timing-retry logic |
| `failure_reason` | string | One of the 8 root causes from the spec (`expired_card`, `insufficient_balance`, `bank_declined`, `card_blocked_frozen`, `upi_autopay_failure`, `payment_gateway_failure`, `account_card_changed`, `bank_fraud_pattern_block`) |
| `cycles_completed` | number | How many billing cycles this user has actually completed (0, 2, 3, 4, or 5) — drives which churn-score formula stage applies |
| `payment_history` | string | Last N completed cycles as a string of 1s/0s (1=paid, 0=missed), most recent last. `"none"` for brand-new users with zero cycles |
| `is_new_user` | boolean | True if `cycles_completed` < 3 — per spec, these users get the flat default score rather than a computed one |
| `churn_score` | number | New users (< 3 cycles): flat 77% default. Otherwise: (payments made ÷ cycles used, capped at 5) × 100, per spec Section 6 |
| `churn_band` | string | Low (80–100%) / Medium (40–79%) / High (0–39%), derived from `churn_score` |

## User history mix (so all formula stages are represented)

| `cycles_completed` | Count | Formula applied |
|---|---|---|
| 0 (brand new, no history) | 8 | Default 77% |
| 2 (still early) | 6 | Default 77% |
| 3 | 10 | (paid ÷ 3) × 100 |
| 4 | 10 | (paid ÷ 4) × 100 |
| 5 | 21 | (paid ÷ 5) × 100 |

## What this feeds

- `failure_reason` → Diagnosis engine (Section 2 of spec)
- `failure_timestamp` → Timing-retry logic (odd-hours detection)
- `churn_score` / `churn_band` → Month 2 reminder throttling (4/3/2)
- All fields → Audit trail logging once the recovery engine runs against this batch

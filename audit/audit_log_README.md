# audit_log.csv — README

Output of running the full simulation (`src/diagnosis_decision_engine.py` +
`src/retry_engine.py`) against `synthetic_failed_payments.csv` (55 records).

## ⚠️ Important: synthetic outcome model

Whether each account "recovers" is decided by a **made-up probability model**
in `retry_engine.py` (`OVERALL_RECOVERY_PROB`), since no real bank/payment
success-rate data was available:

| Solution branch | Assumed overall recovery chance |
|---|---|
| Timing retry | 72% |
| Delayed retry | 60% |
| Update method | 48% |
| Notify user | 40% |

These numbers are **not measured from anything real** — they exist purely to
produce a runnable, testable, believable simulation for the demo. State this
clearly in the pitch. A production version would replace this with real
observed retry-success rates from actual Razorpay test/live data.

## Result from this run (seed=7, reproducible)

- **37 recovered / 18 unresolved (exception_lapsed)** out of 55 accounts
- **₹14,563 recovered / ₹24,145 total at risk (60.3%)**
- 35 of 37 recoveries happened in **Month 1** (2 in Month 2) — consistent
  with Month 1 being the fast/direct recovery window by design
- Recovery rate varies by branch (timing/delayed retry recover more often
  than update-method/notify-user, which need real user action) — this
  matches the assumed probabilities above, so it's a validation of the
  model's logic, not an independent finding
- Churn-band recovery rates don't show a strong pattern in this run — with
  only 55 records, that's expected noise, not a real signal. A larger batch
  would be needed to see a genuine trend, if one exists.

## Columns

| Column | Description |
|---|---|
| `payment_id`, `user_id`, `amount_inr` | From the original synthetic batch |
| `failure_reason` | Diagnosed root cause |
| `solution_branch` | Decision engine's chosen recovery path |
| `churn_band` | Low/Medium/High, from the original batch |
| `final_status` | `recovered` or `exception_lapsed` |
| `recovered_in_month` | 1 or 2, blank if never recovered |
| `recovered_at_reminder` | Which reminder number it recovered at (within that month) |
| `reminders_sent_month1` / `_month2` | How many reminders actually went out (can be less than the taper max, since the retry-then-check loop stops early on success) |
| `total_reminders_sent` | Sum of both |

## Re-running

`cd src && python3 retry_engine.py` — reproducible via the fixed random seed
(7). Change the seed or `OVERALL_RECOVERY_PROB` values to test other
scenarios.

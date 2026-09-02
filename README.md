# AI Revenue Recovery
**Razorpay AI Buildathon — Track 3 (AI Revenue Recovery)**

An agent that detects failed subscription payments, diagnoses the root cause, and runs a bounded, escalating recovery workflow — with a full audit trail and a measured recovery outcome.

## Result

Running the full pipeline against a synthetic batch of 55 simulated failed payments:

**₹14,563 recovered of ₹24,145 at risk (60.3%)** — 37 accounts recovered, 18 unresolved.

See `dashboard-3.html` for the full interactive breakdown (open in a browser).

## Project structure

| Folder | Contents |
|---|---|
| `docs/` | Full project spec — root causes, decision logic, escalation timeline, churn model |
| `data/` | Synthetic 55-record batch of failed payments used to test the engine |
| `src/` | Diagnosis + decision engine, retry-then-check simulation engine |
| `audit/` | Output audit log from running `src/` against `data/`, with results README |
| `dashboard/` | Self-contained HTML dashboard visualizing the audit log |

## How it works

1. **Diagnosis** (`src/diagnosis_decision_engine.py`) — classifies each failed payment into one of 8 root causes (expired card, insufficient balance, bank declined, card blocked, UPI failure, gateway failure, account changed, fraud-pattern block).
2. **Decision** — maps each cause to one of 4 recovery branches: Timing Retry, Delayed Retry, Update Method, Notify User.
3. **Retry-then-check loop** (`src/retry_engine.py`) — before every reminder after the first, silently retries the payment. Succeeds → stop. Fails → send the next reminder.
4. **Bounded escalation** — Month 1 runs a taper of up to 9 reminders (4/3/1/1 per week), including the failure reason. Month 2 runs up to 4 more (throttled by churn risk: 4/3/2), with plain re-engagement messaging. After Month 2, the account is marked as a terminal exception — no more automated attempts.
5. **Audit trail** — every account's outcome, retry count, and churn band is logged (`audit/audit_log.csv`).

## Run it yourself

```bash
cd src
python3 retry_engine.py
```

Reproducible via a fixed random seed. Outputs a summary to the console and writes a full audit log CSV.

## Important note on synthetic data

This project uses **synthetic data throughout** — a fake failed-payment batch, and a made-up (not real) recovery-likelihood model per solution branch, since no real Razorpay transaction data was available. This is clearly flagged in `data/synthetic_data_README.md` and `audit/audit_log_README.md`. A production version would swap these for real observed data from Razorpay's test/live APIs.


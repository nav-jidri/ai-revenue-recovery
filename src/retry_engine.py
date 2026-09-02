"""
Retry-Then-Check Loop + Escalation Timeline + Audit Log
---------------------------------------------------------
Step 3 of the build order. Simulates, for every failed payment:

  - Month 1: up to 9 reminders total (taper 4+3+1+1 across 4 weeks),
             reason included in messaging, same for every user.
  - Month 2: up to 4/3/2 reminders (churn-throttled), blunt messages
             (Plan B - no personalisation, per latest spec decision).
  - Retry-then-check: before every reminder EXCEPT the very first,
    attempt a silent retry. If it succeeds -> STOP, mark recovered.
    If it fails -> send the next reminder, keep going.
  - If every reminder in the full sequence is exhausted with no
    success -> STOP, mark as terminal/exception (unresolved).

⚠️ SYNTHETIC ASSUMPTION: there's no real bank/payment success-rate
data available, so this script assigns made-up retry-success
probabilities per solution branch, just to produce a believable,
explainable simulation. These numbers are NOT sourced from anything
real — they exist only so the demo has a runnable, testable engine.
Swap in real probabilities (or real Razorpay retry outcomes) later.
"""

import csv
import random
from collections import Counter

from diagnosis_decision_engine import process_batch, BRANCH_LABELS

random.seed(7)  # reproducible simulation

# ---- Escalation timeline constants (from spec Section 4) ----
MONTH1_WEEKLY_TAPER = [4, 3, 1, 1]          # max reminders per week, Month 1
MONTH1_MAX = sum(MONTH1_WEEKLY_TAPER)        # 9 total, ceiling not guaranteed
MONTH2_MAX_BY_BAND = {"Low": 4, "Medium": 3, "High": 2}   # churn-throttled, Section 6

# ---- SYNTHETIC overall recovery-likelihood per branch (assumption, see docstring) ----
# Rather than an escalating per-attempt probability (which mathematically guarantees
# near-100% recovery given ~13 attempts), each account is assigned ONE outcome up front:
# will this cause ever get fixed, no matter how many reminders/retries we throw at it?
# This reflects reality: some failures (e.g. a truly abandoned card, a user who's genuinely
# gone) never resolve no matter how many times you retry — that's exactly why a
# stopping rule and an "exception" bucket need to exist at all.
OVERALL_RECOVERY_PROB = {
    "timing_retry":  0.72,   # mostly a timing/bank-side issue, resolves fairly often
    "delayed_retry": 0.60,   # balance issues resolve once funds/payday catch up
    "update_method": 0.48,   # needs real user action (new card) — harder, less certain
    "notify_user":   0.40,   # mixed bag; hardest to guarantee resolution
}


def simulate_account_outcome(branch, total_possible_attempts, rng):
    """
    Decides, once per account, whether it will EVER recover (given the branch's
    overall likelihood), and if so, at which attempt number (weighted toward
    earlier attempts, since retries/reminders are more effective while the
    issue is fresh). Returns (will_recover: bool, recovery_attempt: int|None).
    ⚠️ SYNTHETIC model — see module docstring.
    """
    will_recover = rng.random() < OVERALL_RECOVERY_PROB[branch]
    if not will_recover:
        return False, None
    # weight earlier attempts more heavily using a simple triangular-ish distribution
    weights = [total_possible_attempts - i for i in range(total_possible_attempts)]
    recovery_attempt = rng.choices(range(1, total_possible_attempts + 1), weights=weights, k=1)[0]
    return True, recovery_attempt


def month1_message(record, reminder_index):
    """Month 1 messaging pattern (Section 4): includes the failure reason."""
    patterns = {
        1: "reason_only",
        2: "outcome_first",
        3: "direct_ask_deadline",
    }
    pattern = patterns.get(reminder_index, "direct_ask_deadline")  # 4th+ = tightened deadline
    return pattern


def run_simulation(records):
    """
    Runs the full retry-then-check loop for every record.
    Returns an audit log: one dict per record with full outcome detail.
    """
    audit_log = []
    rng = random.Random(7)  # reproducible

    for record in records:
        branch = record["solution_branch"]
        churn_band = record["churn_band"]
        month2_max = MONTH2_MAX_BY_BAND[churn_band]
        total_possible_attempts = MONTH1_MAX + month2_max  # e.g. 9 + 4 = 13 max

        will_recover, recovery_attempt = simulate_account_outcome(branch, total_possible_attempts, rng)

        recovered_in_month = None
        recovered_at_reminder = None
        reminders_sent_month1 = 0
        reminders_sent_month2 = 0
        attempts_detail = []

        stop_attempt = recovery_attempt if will_recover else None

        # ---- Month 1 sequence (up to MONTH1_MAX reminders) ----
        recovered = False
        for i in range(1, MONTH1_MAX + 1):
            if stop_attempt is not None and i == stop_attempt:
                recovered = True
                recovered_in_month = 1
                recovered_at_reminder = i
                attempts_detail.append(("month1_retry_check", i, True))
                break
            reminders_sent_month1 += 1
            attempts_detail.append(("month1_reminder_sent", i, month1_message(record, i)))

        # ---- Month 2 sequence (only runs if Month 1 didn't recover it) ----
        if not recovered:
            for j in range(1, month2_max + 1):
                overall_attempt = MONTH1_MAX + j
                if stop_attempt is not None and overall_attempt == stop_attempt:
                    recovered = True
                    recovered_in_month = 2
                    recovered_at_reminder = j
                    attempts_detail.append(("month2_retry_check", j, True))
                    break
                reminders_sent_month2 += 1
                attempts_detail.append(("month2_reminder_sent", j, "blunt_message"))

        final_status = "recovered" if recovered else "exception_lapsed"

        audit_log.append({
            "payment_id": record["payment_id"],
            "user_id": record["user_id"],
            "amount_inr": int(record["amount_inr"]),
            "failure_reason": record["failure_reason"],
            "solution_branch": branch,
            "churn_band": churn_band,
            "final_status": final_status,
            "recovered_in_month": recovered_in_month,
            "recovered_at_reminder": recovered_at_reminder,
            "reminders_sent_month1": reminders_sent_month1,
            "reminders_sent_month2": reminders_sent_month2,
            "total_reminders_sent": reminders_sent_month1 + reminders_sent_month2,
        })

    return audit_log


def write_audit_log(audit_log, path):
    fieldnames = list(audit_log[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_log)


if __name__ == "__main__":
    DATA_PATH = "/mnt/user-data/outputs/synthetic_failed_payments.csv"
    records = process_batch(DATA_PATH)
    audit_log = run_simulation(records)

    print(f"Simulated {len(audit_log)} accounts.\n")

    print("Sample (first 5 outcomes):")
    for a in audit_log[:5]:
        print(f"  {a['payment_id']} | {a['failure_reason']:<25} -> {a['final_status']:<16} "
              f"(recovered_in_month={a['recovered_in_month']}, "
              f"reminders sent: M1={a['reminders_sent_month1']} M2={a['reminders_sent_month2']})")

    status_counts = Counter(a["final_status"] for a in audit_log)
    print(f"\nOutcome summary: {dict(status_counts)}")

    recovered_amount = sum(a["amount_inr"] for a in audit_log if a["final_status"] == "recovered")
    at_risk_amount = sum(a["amount_inr"] for a in audit_log)
    print(f"\n₹ Recovered: {recovered_amount} / ₹ At Risk (total batch): {at_risk_amount} "
          f"({recovered_amount/at_risk_amount*100:.1f}%)")

    write_audit_log(audit_log, "/home/claude/audit_log_preview.csv")
    print("\nFull audit log written to /home/claude/audit_log_preview.csv (preview, not yet in outputs)")

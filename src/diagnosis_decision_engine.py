"""
Diagnosis + Decision Engine
-----------------------------------
Reads the synthetic failed-payment batch, confirms each record's
failure_reason (diagnosis), and maps it to one of the 4 solution
branches defined in the spec, Section 3 (decision).

This is Step 2 of the build order:
  1. Synthetic data          [DONE]
  2. Diagnosis + Decision    <- this file
  3. Retry-then-check loop + Audit log
  4. Dashboard/metrics
"""

import csv

# ---- Section 3 of the spec: Cause -> Solution Branch mapping ----
SOLUTION_MAP = {
    "bank_declined":            "timing_retry",
    "bank_fraud_pattern_block": "timing_retry",
    "insufficient_balance":     "delayed_retry",
    "expired_card":             "update_method",
    "account_card_changed":     "update_method",
    "card_blocked_frozen":      "notify_user",
    "upi_autopay_failure":      "notify_user",
    "payment_gateway_failure":  "notify_user",
}

# Human-readable labels, just for printing/reporting
BRANCH_LABELS = {
    "timing_retry":  "Timing Retry (retry during 10am-5pm, avoid 11pm-7am)",
    "delayed_retry": "Delayed Retry (wait a window, e.g. payday-aligned)",
    "update_method": "Update Method (prompt user for new card/details)",
    "notify_user":   "Notify User (alert to act; gateway failure may get quick retry)",
}


def diagnose(record):
    """
    Diagnosis step: confirm the failure_reason is one we recognise.
    Returns the reason string, or raises if it's an unknown cause
    (fails loudly rather than silently mis-routing a real payment issue).
    """
    reason = record["failure_reason"].strip()
    if reason not in SOLUTION_MAP:
        raise ValueError(f"Unrecognised failure_reason: '{reason}' "
                          f"(payment_id={record.get('payment_id')})")
    return reason


def decide(reason):
    """
    Decision step: map a diagnosed cause to its solution branch.
    """
    return SOLUTION_MAP[reason]


def process_batch(csv_path):
    """
    Runs diagnosis + decision on every record in the batch.
    Returns a list of dicts, each original record plus the
    computed 'solution_branch' field.
    """
    results = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for record in reader:
            reason = diagnose(record)
            branch = decide(reason)
            enriched = dict(record)
            enriched["solution_branch"] = branch
            results.append(enriched)
    return results


if __name__ == "__main__":
    DATA_PATH = "/mnt/user-data/outputs/synthetic_failed_payments.csv"
    results = process_batch(DATA_PATH)

    print(f"Processed {len(results)} records.\n")

    # Show a small preview: first 5 records, reason -> branch
    print("Sample (first 5 records):")
    for r in results[:5]:
        print(f"  {r['payment_id']}  |  {r['failure_reason']:<25} -> {BRANCH_LABELS[r['solution_branch']]}")

    # Quick sanity check: how many records fell into each branch
    from collections import Counter
    branch_counts = Counter(r["solution_branch"] for r in results)
    print("\nBranch distribution across the batch:")
    for branch, count in branch_counts.items():
        print(f"  {branch:<15} {count} records")

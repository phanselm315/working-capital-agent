"""Act 1 -- the Diagnostic. Deterministic working-capital analytics.

This produces the deliverable a working-capital consultant builds by hand:
where cash is trapped, how far DSO sits from a realistic target, how much
cash a disciplined collections effort can release, and which accounts drive
the exposure. No LLM is used here -- the numbers must be exact and auditable.
"""
from __future__ import annotations

import config
from src.ingest import BUCKET_ORDER, customer_rollup

# Probability that a past-due dollar converts to cash in the near term.
_AGE_RECOVERY = {"Current": 1.0, "1-30": 1.0, "31-60": 0.97,
                 "61-90": config.HAIRCUT_61_90, "90+": config.HAIRCUT_90_PLUS}


def _recovery_factor(bucket: str, disputed: bool) -> float:
    factor = _AGE_RECOVERY.get(bucket, 1.0)
    if disputed:
        factor = min(factor, config.HAIRCUT_DISPUTED)
    return factor


def run_diagnostic(inv, cust) -> dict:
    total_ar = float(inv["open_balance"].sum())
    ttm_revenue = float(cust["ttm_revenue"].sum())
    dso = total_ar / ttm_revenue * 365.0

    aging = []
    for b in BUCKET_ORDER:
        sub = inv[inv["aging_bucket"] == b]
        amt = float(sub["open_balance"].sum())
        aging.append({"bucket": b, "amount": amt, "pct": amt / total_ar,
                      "invoices": int(len(sub))})

    past_due = inv[inv["is_past_due"]]
    past_due_total = float(past_due["open_balance"].sum())
    current_total = total_ar - past_due_total

    # Weighted-average payment terms -> a realistic target DSO.
    w_terms = float((inv["terms_days"] * inv["open_balance"]).sum() / total_ar)
    target_dso = w_terms + config.BEST_IN_CLASS_BUFFER_DAYS
    excess_days = max(0.0, dso - target_dso)
    cash_topdown = excess_days / 365.0 * ttm_revenue

    # Bottoms-up: near-term collectible cash sitting in the past-due book.
    if len(past_due):
        recover = past_due.apply(
            lambda r: r["open_balance"] * _recovery_factor(r["aging_bucket"], r["is_disputed"]),
            axis=1)
        past_due_collectible = float(recover.sum())
    else:
        past_due_collectible = 0.0

    disputed = inv[inv["is_disputed"]]
    dispute_amount = float(disputed["open_balance"].sum())

    # Current AR likely to slip, based on each customer's payment history.
    hist_late = inv[(~inv["is_past_due"]) & ((inv["avg_days_to_pay"] - inv["terms_days"]) > 10)]
    at_risk_current = float(hist_late["open_balance"].sum())

    roll = customer_rollup(inv, cust)
    top5_pct = float(roll.head(5)["open_balance"].sum() / total_ar)
    top_customers = roll.head(8)[[
        "customer_id", "customer_name", "open_balance", "past_due_balance",
        "pct_of_ar", "oldest_dpd"]].to_dict("records")

    wadpd = (float((past_due["days_past_due"] * past_due["open_balance"]).sum() / past_due_total)
             if past_due_total else 0.0)

    return {
        "as_of_date": config.AS_OF_DATE.isoformat(),
        "total_ar": total_ar,
        "ttm_revenue": ttm_revenue,
        "invoice_count": int(len(inv)),
        "customer_count": int(inv["customer_id"].nunique()),
        "dso": dso,
        "weighted_avg_terms": w_terms,
        "target_dso": target_dso,
        "excess_days": excess_days,
        "aging": aging,
        "past_due_total": past_due_total,
        "past_due_pct": past_due_total / total_ar,
        "current_total": current_total,
        "weighted_avg_days_past_due": wadpd,
        "cash_release_topdown": cash_topdown,
        "past_due_collectible": past_due_collectible,
        "dispute_amount": dispute_amount,
        "dispute_count": int(len(disputed)),
        "at_risk_current": at_risk_current,
        "top5_concentration": top5_pct,
        "top_customers": top_customers,
    }

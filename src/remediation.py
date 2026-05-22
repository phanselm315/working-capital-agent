"""Act 2 -- Remediation. Segments the book and builds the collector worklist.

Segmentation and prioritization are deterministic and rules-based so the
output is defensible. The LLM is only used afterwards, to draft the outreach
for each account on the worklist (see agent.py).
"""
from __future__ import annotations

import datetime as dt

import config
from src.ingest import customer_invoices, customer_rollup

SEGMENT_TONE = {
    "Strategic": "Warm, relationship-first",
    "Standard": "Professional and direct",
    "Chronic Late": "Firm, pattern-aware",
    "High Risk": "Firm, escalation footing",
}
RISK_MULT = {"High Risk": 1.40, "Chronic Late": 1.15, "Strategic": 1.00, "Standard": 1.00}


def classify_segment(row) -> str:
    """Mutually exclusive segment. Escalation risk outranks account size."""
    if row["oldest_dpd"] >= config.HIGH_RISK_PAST_DUE_DAYS:
        return "High Risk"
    if row["ttm_revenue"] >= config.STRATEGIC_TTM_REVENUE:
        return "Strategic"
    if row["days_paid_late"] >= config.CHRONIC_LATE_DAYS:
        return "Chronic Late"
    return "Standard"


def _recommended_action(row) -> str:
    if row["disputed_balance"] > 0:
        return "Resolve dispute, then collect"
    if row["oldest_dpd"] >= 75:
        return "Escalate -- call + formal notice"
    if row["oldest_dpd"] >= 35:
        return "Call AP contact directly"
    return "Send payment reminder"


def build_segments(inv, cust):
    """Customer rollup with a segment label attached."""
    roll = customer_rollup(inv, cust)
    roll["segment"] = roll.apply(classify_segment, axis=1)
    return roll


def build_worklist(segments, inv, size=None):
    """Top-N past-due accounts, priority-ranked, with invoice detail attached."""
    size = size or config.WORKLIST_SIZE
    cand = segments[segments["past_due_balance"] > 0].copy()

    # Priority = dollars x age pressure x segment risk.
    cand["priority_score"] = (
        cand["past_due_balance"]
        * (1.0 + cand["oldest_dpd"] / 60.0)
        * cand["segment"].map(RISK_MULT))
    cand = cand.sort_values("priority_score", ascending=False).head(size).reset_index(drop=True)

    follow_up = (config.AS_OF_DATE + dt.timedelta(days=config.FOLLOW_UP_DAYS)).isoformat()
    items = []
    for i, r in cand.iterrows():
        items.append({
            "rank": i + 1,
            "customer_id": r["customer_id"],
            "customer_name": r["customer_name"],
            "segment": r["segment"],
            "industry": r["industry"],
            "contact_name": r["contact_name"],
            "contact_email": r["contact_email"],
            "payment_terms": r["payment_terms"],
            "open_balance": float(r["open_balance"]),
            "past_due_balance": float(r["past_due_balance"]),
            "past_due_count": int(r["past_due_count"]),
            "oldest_dpd": int(r["oldest_dpd"]),
            "disputed_balance": float(r["disputed_balance"]),
            "ttm_revenue": float(r["ttm_revenue"]),
            "avg_days_to_pay": int(r["avg_days_to_pay"]),
            "days_paid_late": int(r["days_paid_late"]),
            "recommended_action": _recommended_action(r),
            "tone": SEGMENT_TONE[r["segment"]],
            "follow_up_date": follow_up,
            "priority_score": float(r["priority_score"]),
            "invoices": customer_invoices(inv, r["customer_id"]),
        })
    return items


def segment_summary(segments):
    """Aggregate AR and counts by segment for the dashboard."""
    rows = []
    for seg, grp in segments.groupby("segment"):
        rows.append({
            "segment": seg,
            "customers": int(len(grp)),
            "open_balance": float(grp["open_balance"].sum()),
            "past_due_balance": float(grp["past_due_balance"].sum()),
        })
    return sorted(rows, key=lambda x: x["open_balance"], reverse=True)

"""Load the AR aging snapshot and customer master, and shape them for the engine.

The two input CSVs deliberately mirror what a real ERP (NetSuite, QuickBooks,
Sage, Dynamics) exports: an open-invoice aging report and a customer master.
Everything downstream works off the enriched frames this module returns.
"""
from __future__ import annotations

import pandas as pd

import config

TERM_DAYS = {"Net 15": 15, "Net 30": 30, "Net 45": 45, "Net 60": 60}
BUCKET_ORDER = ["Current", "1-30", "31-60", "61-90", "90+"]


def _bucket(dpd: int) -> str:
    if dpd <= 0:
        return "Current"
    if dpd <= 30:
        return "1-30"
    if dpd <= 60:
        return "31-60"
    if dpd <= 90:
        return "61-90"
    return "90+"


def load_data(aging_csv=None, customers_csv=None):
    """Return (invoices, customers) DataFrames; invoices enriched with derived fields."""
    inv = pd.read_csv(aging_csv or config.AR_AGING_CSV, parse_dates=["invoice_date", "due_date"])
    cust = pd.read_csv(customers_csv or config.CUSTOMERS_CSV)

    as_of = pd.Timestamp(config.AS_OF_DATE)
    inv["days_past_due"] = (as_of - inv["due_date"]).dt.days
    inv["aging_bucket"] = inv["days_past_due"].apply(_bucket)
    inv["is_past_due"] = inv["days_past_due"] > 0
    inv["is_disputed"] = inv["dispute_flag"].astype(str).str.upper().eq("Y")
    inv["terms_days"] = inv["payment_terms"].map(TERM_DAYS).fillna(30).astype(int)

    attrs = ["customer_id", "ttm_revenue", "avg_days_to_pay", "invoices_ttm",
             "invoices_late_ttm", "contact_name", "contact_email", "industry"]
    inv = inv.merge(cust[attrs], on="customer_id", how="left")
    return inv, cust


def customer_rollup(inv, cust):
    """One row per customer: open AR, past-due exposure, disputes and pay behavior."""
    pd_mask = inv["is_past_due"]
    by_cust = inv.groupby("customer_id")

    roll = pd.DataFrame(index=cust["customer_id"])
    roll["open_balance"] = by_cust["open_balance"].sum()
    roll["invoice_count"] = by_cust.size()
    roll["current_balance"] = inv[~pd_mask].groupby("customer_id")["open_balance"].sum()
    roll["past_due_balance"] = inv[pd_mask].groupby("customer_id")["open_balance"].sum()
    roll["past_due_count"] = inv[pd_mask].groupby("customer_id").size()
    roll["oldest_dpd"] = inv[pd_mask].groupby("customer_id")["days_past_due"].max()
    roll["disputed_balance"] = inv[inv["is_disputed"]].groupby("customer_id")["open_balance"].sum()
    roll = roll.fillna({"current_balance": 0, "past_due_balance": 0, "past_due_count": 0,
                        "oldest_dpd": 0, "disputed_balance": 0})

    cust_attrs = cust.set_index("customer_id")[[
        "customer_name", "industry", "contact_name", "contact_email", "payment_terms",
        "ttm_revenue", "avg_days_to_pay", "invoices_ttm", "invoices_late_ttm"]]
    roll = roll.join(cust_attrs)

    total_ar = roll["open_balance"].sum()
    roll["pct_of_ar"] = roll["open_balance"] / total_ar
    roll["terms_days"] = roll["payment_terms"].map(TERM_DAYS).fillna(30).astype(int)
    roll["days_paid_late"] = (roll["avg_days_to_pay"] - roll["terms_days"]).clip(lower=0)

    roll = roll.reset_index()
    return roll.sort_values("open_balance", ascending=False).reset_index(drop=True)


def customer_invoices(inv, customer_id):
    """Open invoices for one customer, newest-overdue first -- used in drafting."""
    sub = inv[inv["customer_id"] == customer_id].sort_values("days_past_due", ascending=False)
    return [{
        "invoice_id": r["invoice_id"],
        "invoice_date": r["invoice_date"].date().isoformat(),
        "due_date": r["due_date"].date().isoformat(),
        "open_balance": float(r["open_balance"]),
        "days_past_due": int(r["days_past_due"]),
        "aging_bucket": r["aging_bucket"],
        "disputed": bool(r["is_disputed"]),
        "dispute_reason": r["dispute_reason"] if isinstance(r["dispute_reason"], str) else "",
    } for _, r in sub.iterrows()]

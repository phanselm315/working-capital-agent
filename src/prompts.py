"""Every LLM prompt the agent uses, in one place.

Prompts live here -- not buried in the engine -- so a reviewer can read
exactly what the agent asks Claude to do. They are deliberately explicit
about role, audience, constraints and output format.
"""
from __future__ import annotations


def _usd(x) -> str:
    return f"${x:,.0f}"


# ===========================================================================
# Act 1 -- the diagnostic narrative
# ===========================================================================

DIAGNOSTIC_SYSTEM = """You are a working-capital advisor. You write the \
executive narrative that accompanies an accounts-receivable diagnostic for \
the CFO of a private-equity-backed portfolio company.

Rules:
- The audience is a CFO and a PE deal partner. Assume full financial fluency.
- Be specific and quantitative. Use only the numbers provided; invent nothing.
- Lead with the conclusion: how much cash is trapped, and why.
- Exactly three short paragraphs, about 220 words total. No bullet points,
  no headings, no markdown.
- Plain, direct, board-ready prose. No hedging, no filler. Do not use the
  words "robust" or "delve", and do not use "leverage" as a verb.
- Close on the single highest-priority action."""


def diagnostic_user(d: dict) -> str:
    aging = "\n".join(
        f"  {a['bucket']:>8}: {_usd(a['amount'])} ({a['pct'] * 100:.1f}% of AR)"
        for a in d["aging"])
    return f"""Write the diagnostic narrative from these figures.

AR snapshot as of {d['as_of_date']}
  Total open AR:               {_usd(d['total_ar'])}
  TTM revenue:                 {_usd(d['ttm_revenue'])}
  Open invoices / customers:   {d['invoice_count']} / {d['customer_count']}
  DSO:                         {d['dso']:.1f} days
  Weighted-average terms:      {d['weighted_avg_terms']:.1f} days
  Target DSO (terms + buffer): {d['target_dso']:.1f} days
  Excess days vs. target:      {d['excess_days']:.1f} days

Aging:
{aging}

  Past-due AR:                 {_usd(d['past_due_total'])} ({d['past_due_pct'] * 100:.1f}% of AR)
  Disputed AR:                 {_usd(d['dispute_amount'])} across {d['dispute_count']} invoices
  Current AR likely to slip
    (based on payer history):  {_usd(d['at_risk_current'])}
  Top-5 customer concentration: {d['top5_concentration'] * 100:.1f}% of AR

Cash opportunity:
  Structural (DSO to target):  {_usd(d['cash_release_topdown'])}
  Near-term collectible
    (past-due, risk-adjusted): {_usd(d['past_due_collectible'])}
"""


# ===========================================================================
# Act 2 -- collection outreach
# ===========================================================================

EMAIL_SYSTEM = """You are a senior accounts-receivable specialist drafting \
collection outreach on behalf of the seller. Each email goes to a customer's \
accounts-payable contact.

Rules:
- Match the tone you are told to use; tone is set by the account segment.
- Be specific: name overdue invoice numbers, amounts and ages exactly as
  given. Never invent invoices or numbers.
- State the total past-due amount and make one clear, time-bound ask.
- Offer a constructive path: confirm a remittance date, take a call, or for
  disputed invoices, resolve the specific issue first.
- 110-170 words. No bullet lists in the body. Professional -- never
  aggressive, never groveling. Protect the commercial relationship.
- If any invoice is disputed, address the dispute explicitly and do not
  demand payment on the disputed portion.
- Output exactly this format and nothing else:

Subject: <subject line>

<email body>

End the email body with "Best regards," on its own line, followed by
"Accounts Receivable Team" on the next line."""


def email_user(item: dict) -> str:
    lines = []
    for v in item["invoices"]:
        status = (f"{v['days_past_due']} days past due" if v["days_past_due"] > 0
                  else "not yet due")
        tag = f"  [DISPUTED: {v['dispute_reason']}]" if v["disputed"] else ""
        lines.append(f"  {v['invoice_id']}  due {v['due_date']}  "
                      f"{_usd(v['open_balance'])}  ({status}){tag}")
    disputed = item["disputed_balance"] > 0
    return f"""Draft a collection email for this account.

Customer:           {item['customer_name']} ({item['industry']})
AP contact:         {item['contact_name']}
Account segment:    {item['segment']}
Tone to use:        {item['tone']}
Payment terms:      {item['payment_terms']}
Total past due:     {_usd(item['past_due_balance'])} across {item['past_due_count']} invoice(s)
Oldest item:        {item['oldest_dpd']} days past due
Disputed exposure:  {('YES -- ' + _usd(item['disputed_balance']) + ' in dispute') if disputed else 'none'}
Recommended action: {item['recommended_action']}

Open invoices:
{chr(10).join(lines)}

Write the email now."""

"""Run the Working Capital Agent from the command line.

    python run_demo.py

Runs the full agent pipeline and prints the diagnostic, the customer
segmentation, and the prioritized collector worklist with drafted outreach.
With no ANTHROPIC_API_KEY set, it runs in demo mode using cached Claude
output -- no key and no network required.
"""
from __future__ import annotations

import textwrap

from src import agent

W = 78


def usd(x) -> str:
    return f"${x:,.0f}"


def rule(ch: str = "-"):
    print(ch * W)


def wrap(text: str, width: int = 74):
    out = []
    for line in text.split("\n"):
        line = line.rstrip()
        out.extend(textwrap.wrap(line, width=width) if line else [""])
    return out


def main():
    print()
    rule("=")
    print("  WORKING CAPITAL AGENT")
    rule("=")
    result = agent.run(progress=lambda m: print(f"  ... {m}"))
    d = result.diagnostic
    mode = "DEMO MODE (cached Claude output)" if result.demo_mode else "LIVE (Anthropic API)"

    print()
    rule("=")
    print(f"  ACT 1 -- DIAGNOSTIC      as of {d['as_of_date']}   |   {mode}")
    rule("=")
    print(f"  Total open AR     {usd(d['total_ar']):>16}")
    print(f"  TTM revenue       {usd(d['ttm_revenue']):>16}")
    print(f"  DSO               {d['dso']:>11.1f} days   (target {d['target_dso']:.1f}, "
          f"{d['excess_days']:.1f} days excess)")
    print(f"  Past-due AR       {usd(d['past_due_total']):>16}   "
          f"({d['past_due_pct'] * 100:.0f}% of AR)")
    print(f"  Disputed AR       {usd(d['dispute_amount']):>16}   "
          f"({d['dispute_count']} invoices)")
    print()
    print("  AR aging:")
    for a in d["aging"]:
        bar = "#" * int(round(a["pct"] * 44))
        print(f"    {a['bucket']:>8}  {usd(a['amount']):>13}  {a['pct'] * 100:5.1f}%  {bar}")
    print()
    print("  CASH OPPORTUNITY")
    print(f"    Structural (close DSO to target):   {usd(d['cash_release_topdown'])}")
    print(f"    Near-term collectible (past-due):   {usd(d['past_due_collectible'])}")
    print()
    print("  Diagnostic narrative (written by Claude):")
    for line in wrap(result.narrative, 72):
        print(f"    {line}")

    print()
    rule("=")
    print("  ACT 2 -- SEGMENTATION")
    rule("=")
    for s in result.segment_summary:
        print(f"  {s['segment']:<14} {s['customers']:>2} customers    "
              f"open {usd(s['open_balance']):>13}    "
              f"past-due {usd(s['past_due_balance']):>13}")

    print()
    rule("=")
    print(f"  ACT 2 -- COLLECTOR WORKLIST   ({len(result.worklist)} priority accounts this week)")
    rule("=")
    for w in result.worklist:
        print()
        print(f"  #{w['rank']}  {w['customer_name']}   [{w['segment']}]")
        print(f"      Past due {usd(w['past_due_balance'])} across {w['past_due_count']} "
              f"invoice(s)  |  oldest {w['oldest_dpd']}d  |  {w['recommended_action']}")
        print(f"      To: {w['contact_name']} ({w['contact_email']})")
        print(f"      Subject: {w['email_subject']}")
        for line in wrap(w["email_body"], 68):
            print(f"      | {line}")

    print()
    rule("=")
    total = sum(w["past_due_balance"] for w in result.worklist)
    print(f"  Worklist past-due exposure addressed this run: {usd(total)}")
    if result.demo_mode:
        print("  Running in demo mode. Add ANTHROPIC_API_KEY to .env for live drafting.")
    rule("=")
    print()


if __name__ == "__main__":
    main()

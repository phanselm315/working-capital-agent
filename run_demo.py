"""Run the Working Capital Agent from the command line.

    python run_demo.py

Runs the full agent pipeline and prints the diagnostic, the customer
segmentation, and the prioritized collector worklist with drafted outreach --
then rolls the diagnostic up across the whole fund into the treasury view.
With no ANTHROPIC_API_KEY set, it runs in demo mode using cached Claude
output -- no key and no network required.
"""
from __future__ import annotations

import textwrap

from src import agent, treasury

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
    print("  Every draft above is staged for human approval before send -- see the")
    print("  Approval Queue tab in the dashboard (streamlit run app.py).")
    if result.demo_mode:
        print("  Running in demo mode. Add ANTHROPIC_API_KEY to .env for live drafting.")
    rule("=")

    # ----------------------------------------------------------------- Treasury
    print()
    rule("=")
    print("  TREASURY -- FUND-LEVEL ROLLUP")
    rule("=")
    t = treasury.run_treasury()
    f = t["fund"]
    print(f"  {f['fund_name']}   ({f['company_count']} portfolio companies)")
    print("  Working-capital improvement -> EBITDA lift -> (entry multiple) -> MOIC lift.")
    print()
    for r in t["companies"]:
        c, b, dg = r.company, r.bridge, r.diagnostic
        print(f"  {c['company_name']:<28} {c['entry_multiple']:>4.1f}x entry   "
              f"DSO {dg['dso']:>3.0f}d   invested {usd(c['fund_invested_equity']):>12}")
        print(f"      trapped cash {usd(b['cash_release']):>12}   "
              f"EBITDA lift {usd(b['ebitda_lift']):>9} ({b['ebitda_lift_pct'] * 100:>2.0f}%)"
              f"   MOIC lift +{b['moic_lift_total']:.2f}x")
    print()
    print(f"  FUND  trapped working capital : {usd(f['total_cash_release'])}")
    print(f"  FUND  run-rate EBITDA lift    : {usd(f['total_ebitda_lift'])}  "
          f"({f['total_ebitda_lift_pct'] * 100:.1f}% of fund EBITDA)")
    print(f"  FUND  implied EV created      : {usd(f['total_ev_gain'])}  "
          f"at {f['blended_entry_multiple']:.1f}x blended")
    print(f"  FUND  value created to fund   : {usd(f['fund_value_total'])}")
    print(f"  FUND  implied MOIC lift       : operating +{f['moic_lift_operating']:.2f}x   "
          f"deleveraging +{f['moic_lift_cash']:.2f}x   total +{f['moic_lift_total']:.2f}x")
    print(f"  (on {usd(f['invested_equity'])} invested equity; entry multiples held flat)")
    rule("=")
    print()


if __name__ == "__main__":
    main()

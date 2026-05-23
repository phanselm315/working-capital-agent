"""Treasury -- the fund-level rollup.

Runs the Act 1 diagnostic across every company in the fund and rolls the
results into one value bridge:

  working-capital improvement
    -> a recurring EBITDA lift   disciplined collections recovers aged and
                                 disputed AR the status-quo process writes
                                 off. Avoided bad-debt expense is recurring,
                                 above-the-line EBITDA.
    -> enterprise value created  the EBITDA lift valued at the EV/EBITDA
                                 multiple the asset was bought at.
    -> a MOIC lift               on the fund's invested equity.

The one-time working-capital cash release is tracked alongside and valued
1:1 against equity, since it pays down net debt. Every figure here is
deterministic arithmetic -- no LLM is involved, so the rollup is exact and
auditable, exactly like the Act 1 diagnostic it is built on.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

import config
from src import diagnostic, ingest


@dataclass
class CompanyResult:
    company: dict      # portfolio.csv row enriched with derived entry economics
    diagnostic: dict   # the Act 1 diagnostic for this company
    bridge: dict       # the working-capital -> EBITDA -> MOIC value bridge


def load_portfolio() -> list:
    """Read the fund master (portfolio.csv) and derive entry economics.

    Entry EV     = entry EBITDA x entry multiple
    Entry equity = entry EV - entry net debt
    Fund invested= entry equity x the fund's ownership stake
    """
    df = pd.read_csv(config.PORTFOLIO_CSV)
    companies = []
    for _, r in df.iterrows():
        entry_ebitda = float(r["entry_ebitda"])
        entry_multiple = float(r["entry_multiple"])
        entry_net_debt = float(r["entry_net_debt"])
        ownership = float(r["fund_ownership_pct"])
        entry_ev = entry_ebitda * entry_multiple
        entry_equity = entry_ev - entry_net_debt
        companies.append({
            "company_id": str(r["company_id"]),
            "company_name": str(r["company_name"]),
            "sector": str(r["sector"]),
            "entry_date": str(r["entry_date"]),
            "entry_ebitda": entry_ebitda,
            "entry_multiple": entry_multiple,
            "entry_net_debt": entry_net_debt,
            "entry_ev": entry_ev,
            "entry_equity": entry_equity,
            "fund_ownership_pct": ownership,
            "fund_invested_equity": entry_equity * ownership,
            "ar_aging_file": config.ROOT / str(r["ar_aging_file"]),
            "customers_file": config.ROOT / str(r["customers_file"]),
        })
    return companies


def _ninety_plus(diag: dict) -> float:
    """Open AR sitting in the 90+ day aging bucket."""
    return next((a["amount"] for a in diag["aging"] if a["bucket"] == "90+"), 0.0)


def write_off_risk_ar(diag: dict) -> float:
    """The AR pool genuinely exposed to write-off: disputed dollars + 90+ days.

    This is intentionally narrow -- not all past-due AR, only the dollars a
    status-quo process realistically loses to bad debt. The EBITDA-lift model
    works from this pool, not from the headline past-due number.
    """
    return diag["dispute_amount"] + _ninety_plus(diag)


def company_bridge(company: dict, diag: dict) -> dict:
    """Build the working-capital -> EBITDA -> MOIC value bridge for one company.

    Two value channels, kept separate on purpose:

    Operating channel  -- the recurring EBITDA lift (a share of the write-off-
                          risk AR the agent's process converts back to cash),
                          valued at the entry EV/EBITDA multiple.
    Cash channel       -- the one-time structural DSO cash release, valued 1:1
                          against equity as it pays down net debt.
    """
    cash_release = diag["cash_release_topdown"]                 # one-time WC release
    at_risk = write_off_risk_ar(diag)
    ebitda_lift = config.BAD_DEBT_RECOVERY_UPLIFT * at_risk     # recurring run-rate

    # HOLD_ENTRY_MULTIPLE: value the lift at the multiple the asset was bought
    # at -- no multiple expansion assumed, so value creation is purely operational.
    multiple = company["entry_multiple"]
    ev_gain = ebitda_lift * multiple                            # operational EV created
    entry_equity = company["entry_equity"]
    ownership = company["fund_ownership_pct"]

    return {
        "cash_release": cash_release,
        "write_off_risk_ar": at_risk,
        "ebitda_lift": ebitda_lift,
        "ebitda_lift_pct": ebitda_lift / company["entry_ebitda"],
        "ev_gain": ev_gain,
        # equity value created -- 100% basis
        "equity_value_operating": ev_gain,
        "equity_value_cash": cash_release,
        "equity_value_total": ev_gain + cash_release,
        # the fund's share of that value, at its ownership stake
        "fund_value_operating": ev_gain * ownership,
        "fund_value_cash": cash_release * ownership,
        "fund_value_total": (ev_gain + cash_release) * ownership,
        # MOIC lift is a ratio on invested equity, so ownership cancels
        "moic_lift_operating": ev_gain / entry_equity,
        "moic_lift_cash": cash_release / entry_equity,
        "moic_lift_total": (ev_gain + cash_release) / entry_equity,
    }


def _rollup(results: list) -> dict:
    """Aggregate the per-company bridges into one fund-level view."""
    sum_invested = sum(r.company["fund_invested_equity"] for r in results)
    sum_equity = sum(r.company["entry_equity"] for r in results)
    sum_ev = sum(r.company["entry_ev"] for r in results)
    sum_ebitda = sum(r.company["entry_ebitda"] for r in results)
    cash = sum(r.bridge["cash_release"] for r in results)
    ebitda_lift = sum(r.bridge["ebitda_lift"] for r in results)
    ev_gain = sum(r.bridge["ev_gain"] for r in results)
    fv_op = sum(r.bridge["fund_value_operating"] for r in results)
    fv_cash = sum(r.bridge["fund_value_cash"] for r in results)
    fv_total = sum(r.bridge["fund_value_total"] for r in results)
    return {
        "fund_name": config.FUND_NAME,
        "company_count": len(results),
        "as_of_date": results[0].diagnostic["as_of_date"] if results else None,
        "invested_equity": sum_invested,
        "entry_equity": sum_equity,
        "entry_ev": sum_ev,
        "entry_ebitda": sum_ebitda,
        "blended_entry_multiple": sum_ev / sum_ebitda,
        "total_cash_release": cash,
        "total_ebitda_lift": ebitda_lift,
        "total_ebitda_lift_pct": ebitda_lift / sum_ebitda,
        "total_ev_gain": ev_gain,
        "fund_value_operating": fv_op,
        "fund_value_cash": fv_cash,
        "fund_value_total": fv_total,
        # fund MOIC lift -- weighted by the fund's invested dollars
        "moic_lift_operating": fv_op / sum_invested,
        "moic_lift_cash": fv_cash / sum_invested,
        "moic_lift_total": fv_total / sum_invested,
    }


def run_treasury() -> dict:
    """Run the diagnostic + value bridge for every fund company.

    Returns {"fund": <rollup dict>, "companies": [CompanyResult, ...]}.
    """
    results = []
    for company in load_portfolio():
        inv, cust = ingest.load_data(company["ar_aging_file"], company["customers_file"])
        diag = diagnostic.run_diagnostic(inv, cust)
        bridge = company_bridge(company, diag)
        results.append(CompanyResult(company=company, diagnostic=diag, bridge=bridge))
    return {"fund": _rollup(results), "companies": results}


def _usd(x) -> str:
    return f"${x:,.0f}"


if __name__ == "__main__":
    t = run_treasury()
    f = t["fund"]
    W = 78
    print()
    print("=" * W)
    print(f"  TREASURY -- {f['fund_name']}")
    print(f"  {f['company_count']} portfolio companies   |   AR snapshot as of {f['as_of_date']}")
    print("=" * W)
    for r in t["companies"]:
        c, d, b = r.company, r.diagnostic, r.bridge
        print(f"  {c['company_name']:<28} {c['sector']}")
        print(f"      entry {c['entry_multiple']:.1f}x  |  invested {_usd(c['fund_invested_equity'])}"
              f"  |  DSO {d['dso']:.0f}d")
        print(f"      trapped cash {_usd(b['cash_release'])}  |  EBITDA lift {_usd(b['ebitda_lift'])}"
              f" ({b['ebitda_lift_pct'] * 100:.0f}%)  |  EV gain {_usd(b['ev_gain'])}")
        print(f"      MOIC lift  operating +{b['moic_lift_operating']:.2f}x"
              f"   deleveraging +{b['moic_lift_cash']:.2f}x"
              f"   total +{b['moic_lift_total']:.2f}x")
        print()
    print("-" * W)
    print(f"  FUND ROLLUP")
    print(f"    Invested equity            {_usd(f['invested_equity'])}")
    print(f"    Blended entry multiple     {f['blended_entry_multiple']:.1f}x")
    print(f"    Trapped working capital    {_usd(f['total_cash_release'])}")
    print(f"    Run-rate EBITDA lift       {_usd(f['total_ebitda_lift'])}"
          f"  ({f['total_ebitda_lift_pct'] * 100:.1f}% of fund EBITDA)")
    print(f"    Implied EV created         {_usd(f['total_ev_gain'])}")
    print(f"    Value created to the fund  {_usd(f['fund_value_total'])}")
    print(f"    Implied MOIC lift          operating +{f['moic_lift_operating']:.2f}x"
          f"   deleveraging +{f['moic_lift_cash']:.2f}x   total +{f['moic_lift_total']:.2f}x")
    print("=" * W)
    print()

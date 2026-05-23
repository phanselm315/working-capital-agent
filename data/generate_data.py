"""Synthetic AR data generator for the Working Capital Agent.

Produces two CSVs that mimic a real ERP export:
  data/customers.csv  -- customer master with payment history
  data/ar_aging.csv   -- open invoices (an AR aging snapshot)

The data is 100% synthetic and seeded, so the diagnostic is reproducible.
Customers are built from five behavioral archetypes on purpose, so the
diagnostic surfaces a clear, teachable story:

  anchor      large, pay on time           -> revenue concentration, low risk
  steady      mid-size, pay near terms     -> healthy core
  chronic     mid-size, chronically late   -> the core collection opportunity
  distressed  aged balances, dispute risk  -> escalation / bad-debt watch
  small       small accounts, mixed        -> long tail

Run:  python data/generate_data.py
"""
from __future__ import annotations

import random
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

SEED = 4726
rng = random.Random(SEED)
AS_OF = config.AS_OF_DATE

TERM_DAYS = {"Net 15": 15, "Net 30": 30, "Net 45": 45, "Net 60": 60}

# Behavioral archetypes. `late` is days paid beyond stated terms.
ARCHETYPES = {
    "anchor":     dict(n=5,  ttm=(1_500_000, 3_400_000), terms=["Net 45", "Net 60"],
                       late=(-3, 9),  ninv=(3, 6), latefrac=0.10),
    "steady":     dict(n=10, ttm=(450_000, 1_150_000),   terms=["Net 30", "Net 30", "Net 45"],
                       late=(2, 13),  ninv=(2, 5), latefrac=0.28),
    "chronic":    dict(n=12, ttm=(350_000, 980_000),     terms=["Net 30", "Net 30", "Net 45"],
                       late=(21, 45), ninv=(4, 8), latefrac=0.70),
    "distressed": dict(n=5,  ttm=(550_000, 1_500_000),   terms=["Net 30", "Net 45"],
                       late=(48, 88), ninv=(4, 9), latefrac=0.86),
    "small":      dict(n=8,  ttm=(60_000, 280_000),      terms=["Net 15", "Net 30"],
                       late=(0, 22),  ninv=(1, 4), latefrac=0.34),
}

NAMES = {
    "anchor": ["Cascade Industrial Group", "Northwind Manufacturing", "Sterling Components Corp",
               "Pacifica Materials Co", "Granite Peak Industries"],
    "steady": ["Birch & Hollow Supply", "Cedar Valley Distribution", "Riverstone Packaging",
               "Halcyon Tool Works", "Brightline Logistics", "Copperfield Equipment",
               "Aspen Grove Products", "Tidewater Fabrication", "Maple Ridge Hardware",
               "Lakeshore Components"],
    "chronic": ["Vanguard Metalworks", "Ironclad Supply Co", "Summit Crest Trading",
                "Delta Bay Wholesale", "Pinewood Industrial", "Crossroads Distributors",
                "Harbor Point Mfg", "Redwood Hollow Co", "Stonebridge Parts",
                "Eastgate Materials", "Clearwater Industrial", "Foundry Lane Supply"],
    "distressed": ["Apex Holdings Group", "Beacon Street Trading", "Lighthouse Industrial",
                   "Keystone Freight Co", "Old Mill Manufacturing"],
    "small": ["Junction Box LLC", "Two Rivers Workshop", "Hilltop Supply", "Anchor & Co Trading",
              "Maple Street Mfg", "Quail Run Hardware", "Bramble Hill Goods", "Fox Hollow Supply"],
}

INDUSTRIES = ["Industrial Distribution", "Contract Manufacturing", "Packaging & Materials",
              "Freight & Logistics", "Building Products", "Fabricated Metals",
              "Industrial Equipment", "Wholesale Trade"]

FIRST = ["Karen", "Mike", "Susan", "Dave", "Linda", "Tom", "Janet", "Greg", "Patty", "Ron",
         "Diane", "Carl", "Nancy", "Steve", "Brenda", "Phil", "Donna", "Gary", "Lori", "Frank",
         "Cindy", "Mark", "Joan", "Ed", "Sheila", "Wayne", "Paula", "Dennis", "Rhonda", "Neil",
         "Vicki", "Bruce", "Marcia", "Glenn", "Tina", "Roy", "Debra", "Lyle", "Connie", "Stan"]
LAST = ["Boyd", "Hahn", "Mercer", "Pruitt", "Vance", "Doyle", "Ramsey", "Kessler", "Tran",
        "Whitfield", "Salas", "Mathis", "Coleman", "Padilla", "Burkhart", "Yoon", "Easton",
        "Crowe", "Devlin", "Ngo", "Frost", "Abbott", "Means", "Cobb", "Reyes", "Pope",
        "Schaffer", "Lund", "Pratt", "Hines", "Beck", "Marsh", "Quinn", "Stearns", "Calder",
        "Webb", "Roche", "Hartley", "Dunn", "Voss"]

DISPUTE_REASONS = ["Pricing discrepancy vs. PO", "Short shipment claim", "Damaged goods reported",
                   "Missing PO number on invoice", "Quantity mismatch on receipt",
                   "Awaiting credit memo", "Freight charges contested"]


def email_slug(name: str) -> str:
    s = name.lower()
    for w in (" & ", " llc", " inc", " corp", " group"):
        s = s.replace(w, " ")
    return "".join(ch for ch in s if ch.isalnum())[:24]


def build():
    customers, invoices = [], []
    inv_seq, cust_seq = 0, 0

    for arch, cfg in ARCHETYPES.items():
        for i in range(cfg["n"]):
            cust_seq += 1
            cid = f"C{cust_seq:03d}"
            name = NAMES[arch][i]
            terms = rng.choice(cfg["terms"])
            tdays = TERM_DAYS[terms]
            ttm = int(round(rng.uniform(*cfg["ttm"]), -3))
            adtp = max(5.0, tdays + rng.uniform(*cfg["late"]))

            inv_ttm = rng.randint(9, 40) if ttm > 300_000 else rng.randint(5, 16)
            inv_late = min(inv_ttm, round(inv_ttm * cfg["latefrac"] * rng.uniform(0.8, 1.15)))

            customers.append(dict(
                customer_id=cid, customer_name=name, industry=rng.choice(INDUSTRIES),
                contact_name=f"{FIRST[(cust_seq * 7) % len(FIRST)]} {LAST[(cust_seq * 5) % len(LAST)]}",
                contact_email=f"ap@{email_slug(name)}.com", payment_terms=terms,
                ttm_revenue=ttm, avg_days_to_pay=int(round(adtp)),
                invoices_ttm=inv_ttm, invoices_late_ttm=inv_late, archetype=arch,
            ))

            # Open invoices: total open balance scales with billings x payment lag.
            monthly = ttm / 12.0
            total_open = monthly * (adtp / 30.0) * rng.uniform(0.82, 1.18)
            n = rng.randint(*cfg["ninv"])
            ages = sorted(rng.uniform(3, max(adtp * 1.3, tdays + 6)) for _ in range(n))
            weights = [rng.uniform(0.5, 1.6) for _ in range(n)]
            wsum = sum(weights)

            for j in range(n):
                inv_seq += 1
                amt = max(200, int(round(total_open * weights[j] / wsum, -1)))
                inv_date = AS_OF - timedelta(days=int(round(ages[j])))
                invoices.append(dict(
                    invoice_id=f"INV-{10000 + inv_seq}", customer_id=cid, customer_name=name,
                    invoice_date=inv_date.isoformat(),
                    due_date=(inv_date + timedelta(days=tdays)).isoformat(),
                    payment_terms=terms, invoice_amount=amt, open_balance=amt,
                    dispute_flag="N", dispute_reason="",
                ))

    # Inject disputes on non-anchor accounts; a few become partial short-pays.
    arch_of = {c["customer_id"]: c["archetype"] for c in customers}
    eligible = [k for k, inv in enumerate(invoices)
                if arch_of[inv["customer_id"]] in ("chronic", "distressed", "steady")]
    for rank, k in enumerate(rng.sample(eligible, 9)):
        invoices[k]["dispute_flag"] = "Y"
        invoices[k]["dispute_reason"] = rng.choice(DISPUTE_REASONS)
        if rank < 4:  # short-pay: customer paid part, disputes the rest
            invoices[k]["open_balance"] = max(
                200, int(round(invoices[k]["invoice_amount"] * rng.uniform(0.4, 0.78), -1)))

    cust_df = pd.DataFrame(customers).drop(columns=["archetype"])
    inv_df = pd.DataFrame(invoices)[
        ["invoice_id", "customer_id", "customer_name", "invoice_date", "due_date",
         "payment_terms", "invoice_amount", "open_balance", "dispute_flag", "dispute_reason"]
    ]

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    cust_df.to_csv(config.CUSTOMERS_CSV, index=False)
    inv_df.to_csv(config.AR_AGING_CSV, index=False)

    total_ar = inv_df["open_balance"].sum()
    total_rev = cust_df["ttm_revenue"].sum()
    print(f"customers          : {len(cust_df)}")
    print(f"open invoices      : {len(inv_df)}")
    print(f"total open AR      : ${total_ar:,.0f}")
    print(f"total TTM revenue  : ${total_rev:,.0f}")
    print(f"implied DSO        : {total_ar / total_rev * 365:.1f} days")
    print(f"disputed invoices  : {(inv_df.dispute_flag == 'Y').sum()}")
    print(f"wrote {config.CUSTOMERS_CSV.name} and {config.AR_AGING_CSV.name}")


# ===========================================================================
# Portfolio generation -- one company is not a fund.
#
# The treasury view needs several companies so the rollup tells a story:
# different sizes, different DSO discipline, different aged/disputed mixes.
# generate_company() is build() made parametric -- same archetype logic,
# scaled and stressed -- so each portfolio company is distinct but built the
# same auditable way. build() above is left untouched; the original
# single-company files are never regenerated by this section.
# ===========================================================================

# company_id, seed, rev_scale (size), stress (>1 = a later, more distressed book)
PORTFOLIO = [
    ("PC2", 5101, 1.75, 0.80),
    ("PC3", 5102, 0.70, 1.45),
    ("PC4", 5103, 1.22, 1.10),
    ("PC5", 5104, 0.56, 1.62),
    ("PC6", 5105, 0.90, 0.92),
    ("PC7", 5106, 5.25, 1.00),
]


def generate_company(seed: int, rev_scale: float = 1.0, stress: float = 1.0):
    """Build one company's (customers_df, invoices_df). Seeded and reproducible.

    rev_scale  scales company size -- customer TTM revenue and billings.
    stress     >1 pushes the receivables book later and more distressed;
               <1 makes it cleaner. Drives DSO and the aged/disputed mix.
    """
    r = random.Random(seed)
    customers, invoices = [], []
    inv_seq = cust_seq = 0

    for arch, cfg in ARCHETYPES.items():
        for i in range(cfg["n"]):
            cust_seq += 1
            cid = f"C{cust_seq:03d}"
            name = NAMES[arch][i]
            terms = r.choice(cfg["terms"])
            tdays = TERM_DAYS[terms]
            ttm = int(round(r.uniform(cfg["ttm"][0] * rev_scale,
                                      cfg["ttm"][1] * rev_scale), -3))
            late_lo, late_hi = cfg["late"]
            adtp = max(5.0, tdays + r.uniform(late_lo * stress, late_hi * stress))
            latefrac = min(0.97, cfg["latefrac"] * stress)

            inv_ttm = r.randint(9, 40) if ttm > 300_000 else r.randint(5, 16)
            inv_late = min(inv_ttm, round(inv_ttm * latefrac * r.uniform(0.8, 1.15)))

            customers.append(dict(
                customer_id=cid, customer_name=name, industry=r.choice(INDUSTRIES),
                contact_name=f"{FIRST[(cust_seq * 7) % len(FIRST)]} {LAST[(cust_seq * 5) % len(LAST)]}",
                contact_email=f"ap@{email_slug(name)}.com", payment_terms=terms,
                ttm_revenue=ttm, avg_days_to_pay=int(round(adtp)),
                invoices_ttm=inv_ttm, invoices_late_ttm=inv_late, archetype=arch,
            ))

            monthly = ttm / 12.0
            total_open = monthly * (adtp / 30.0) * r.uniform(0.82, 1.18)
            n = r.randint(*cfg["ninv"])
            ages = sorted(r.uniform(3, max(adtp * 1.3, tdays + 6)) for _ in range(n))
            weights = [r.uniform(0.5, 1.6) for _ in range(n)]
            wsum = sum(weights)

            for j in range(n):
                inv_seq += 1
                amt = max(200, int(round(total_open * weights[j] / wsum, -1)))
                inv_date = AS_OF - timedelta(days=int(round(ages[j])))
                invoices.append(dict(
                    invoice_id=f"INV-{10000 + inv_seq}", customer_id=cid, customer_name=name,
                    invoice_date=inv_date.isoformat(),
                    due_date=(inv_date + timedelta(days=tdays)).isoformat(),
                    payment_terms=terms, invoice_amount=amt, open_balance=amt,
                    dispute_flag="N", dispute_reason="",
                ))

    # A more stressed book carries more disputes; a few become partial short-pays.
    arch_of = {c["customer_id"]: c["archetype"] for c in customers}
    eligible = [k for k, inv in enumerate(invoices)
                if arch_of[inv["customer_id"]] in ("chronic", "distressed", "steady")]
    n_disp = min(len(eligible), max(5, round(9 * stress)))
    for rank, k in enumerate(r.sample(eligible, n_disp)):
        invoices[k]["dispute_flag"] = "Y"
        invoices[k]["dispute_reason"] = r.choice(DISPUTE_REASONS)
        if rank < max(2, n_disp // 2 - 1):  # short-pay: customer paid part, disputes the rest
            invoices[k]["open_balance"] = max(
                200, int(round(invoices[k]["invoice_amount"] * r.uniform(0.4, 0.78), -1)))

    cust_df = pd.DataFrame(customers).drop(columns=["archetype"])
    inv_df = pd.DataFrame(invoices)[
        ["invoice_id", "customer_id", "customer_name", "invoice_date", "due_date",
         "payment_terms", "invoice_amount", "open_balance", "dispute_flag", "dispute_reason"]
    ]
    return cust_df, inv_df


def build_portfolio():
    """Generate the additional fund companies (PC2-PC6) into data/portfolio/.

    PC1 is the original single-company dataset (data/ar_aging.csv,
    data/customers.csv) and is not touched here -- the fund master
    portfolio.csv points PC1 at those existing files.
    """
    out_dir = config.PORTFOLIO_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    print("Generating fund portfolio companies (PC2-PC6)...")
    for cid, seed, rev_scale, stress in PORTFOLIO:
        cust_df, inv_df = generate_company(seed, rev_scale, stress)
        cust_df.to_csv(out_dir / f"{cid.lower()}_customers.csv", index=False)
        inv_df.to_csv(out_dir / f"{cid.lower()}_ar_aging.csv", index=False)
        total_ar = inv_df["open_balance"].sum()
        total_rev = cust_df["ttm_revenue"].sum()
        disp = int((inv_df.dispute_flag == "Y").sum())
        print(f"  {cid}: {len(cust_df)} customers, {len(inv_df)} invoices, "
              f"AR ${total_ar:,.0f}, rev ${total_rev:,.0f}, "
              f"DSO {total_ar / total_rev * 365:.0f}d, {disp} disputes")
    print(f"wrote {len(PORTFOLIO)} companies to {out_dir}")


if __name__ == "__main__":
    if "--portfolio-only" in sys.argv:
        build_portfolio()
    else:
        build()
        build_portfolio()

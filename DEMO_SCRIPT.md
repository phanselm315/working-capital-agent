# Demo video script — Working Capital Agent

Target length: **3.5–4 minutes**. Goal: show that an agent does, in seconds,
the working-capital diagnostic and collections work a PE firm currently buys
from consultants — that the only inputs are reports any ERP already exports,
that every draft passes a human approval gate, and that the diagnostic rolls
up across the whole fund into an EBITDA and MOIC lift.

## Before you record

- Run live if you can: `cp .env.example .env`, add `ANTHROPIC_API_KEY`, so the
  narrative and emails are written on camera. Demo mode (no key) looks
  identical and is a safe fallback.
- Two windows ready: a terminal (large font) and a browser.
- Have both input CSVs open in the editor for Shot 2 — `data/ar_aging.csv` and
  `data/customers.csv`.
- Pre-start the app once so it is warm: `streamlit run app.py`.

---

## Shot 1 — The problem (0:00–0:25)

**Show:** you on camera, or a single title slide.

> "Every PE firm runs the same play in the first 100 days: free up trapped
> cash. The biggest pool is almost always accounts receivable. Firms pay
> consultants six figures and wait two to three months for a working-capital
> diagnostic. I built an agent that does it in under a minute — and re-runs
> across every company in the portfolio."

## Shot 2 — Where the data comes from (0:25–1:00)

**Show:** `data/ar_aging.csv` open in the editor, then `data/customers.csv`.

> "Before the agent does anything, here's the part that matters most — what it
> actually needs. Just two files: an AR aging report — open invoices by
> customer and age — and a customer master. And neither is a custom data feed.
> Every accounting system already exports both on demand — QuickBooks,
> NetSuite, Sage, Microsoft Dynamics. This is a report your controller already
> runs at every month-end. There's no integration, no API project, no IT
> ticket — you export it and hand it over. The data here is synthetic — 40
> customers, about 200 invoices — but pointing this at a real portfolio company
> is a column-mapping exercise, not a build."

## Shot 3 — Run the agent (1:00–1:30)

**Show:** terminal — type and run `python run_demo.py`. Let the pipeline steps
scroll, then scroll up to the Diagnostic.

> "One command. The agent ingests the data, runs the diagnostic, then has
> Claude write the CFO narrative, segment the customers, and draft the
> outreach. Here's the diagnostic: DSO of 61 days against a 48-day target —
> that 13-day gap is about 1.2 million dollars of cash. And this paragraph is
> written by Claude, board-ready, from the numbers."

## Shot 4 — Show the prompting (1:30–1:45)

**Show:** `src/prompts.py` — scroll the diagnostic and email prompts.

> "Nothing is hidden. Every prompt the agent uses is right here — the math is
> deterministic Python, Claude is used only for the writing and the judgment."

## Shot 5 — The dashboard: diagnostic and worklist (1:45–2:20)

**Show:** browser — the Streamlit app. Click **Run the Working Capital Agent**,
let the status steps play. Walk **Act 1** (metric cards, aging chart,
narrative), then **Act 2**: the segmentation cards and the prioritized
collector worklist.

> "Same agent, with a dashboard. Act 1 is the diagnostic. Act 2 is the part a
> report can't do — a prioritized worklist of the ten accounts to call this
> week, ranked by past-due dollars, age and segment risk."

## Shot 6 — The approval queue (2:20–3:00)

**Show:** the **Approval Queue** tab. Expand **Beacon Street Trading** (firm,
escalatory) and one **Strategic** account to contrast tone. Edit one line of a
draft, set two or three to **Approved to send**, **Hold** one, **Reject** one,
then point at the queue summary and click **Send**.

> "This is the control layer — and the reason the agent is safe to run. It
> drafted an email for every account on the worklist, but it can't send one on
> its own. Every draft lands here first, with four choices: approve, hold,
> edit, or reject. Watch the tone shift by account — firm and escalatory on
> Beacon Street Trading, a 90-day balance; warm on a strategic account that's
> only days late. The drafts are fully editable, so I'll change a line here. I
> approve a few, hold one, reject one — and the queue keeps score: how many are
> cleared to send and the dollars they cover. The send button is gated — only
> what I've approved can go out. The agent does the work; I keep the send
> button."

## Shot 7 — The treasury rollup (3:00–3:40)

**Show:** the **Treasury — Fund View** tab. Walk the headline metrics, the
per-company table, and the MOIC-lift chart.

> "One company is not a fund. The treasury view re-runs that same diagnostic
> across every portfolio company and rolls it into one bridge. The collections
> improvement becomes a recurring EBITDA lift — receivables a status-quo
> process writes off, recovered. Valued at the multiple each company was
> bought at, that's enterprise value created; the cash release deleverages on
> top. Across this seven-company fund: 16.1 million of trapped cash and a
> recurring EBITDA lift that, at the entry multiples, adds an implied 0.13x of
> MOIC — the kind of number a deal partner can underwrite."

## Shot 8 — Close (3:40–4:00)

**Show:** the README comparison table.

> "Six figures and three months becomes a few dollars and one minute — no
> integration, no consultants. Re-run it on every aging refresh, gated by human
> approval, and rolled up to the fund. That's the difference between a
> consulting project and an agent."

---

## If anything goes wrong on camera

- App won't start: `python run_demo.py` alone tells the whole story — it now
  prints the treasury rollup too. Record that and skip the browser.
- Live API hiccup: unset `ANTHROPIC_API_KEY` and re-run; demo mode is instant
  and the output is identical.

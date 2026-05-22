# Demo video script — Working Capital Agent

Target length: **2.5–3 minutes**. Goal: show that an agent does, in seconds,
the working-capital diagnostic and collections work a PE firm currently buys
from consultants — and that it re-runs across every portfolio company.

## Before you record

- Run live if you can: `cp .env.example .env`, add `ANTHROPIC_API_KEY`, so the
  narrative and emails are written on camera. Demo mode (no key) looks
  identical and is a safe fallback.
- Two windows ready: a terminal (large font) and a browser.
- Pre-start the app once so it is warm: `streamlit run app.py`.

---

## Shot 1 — The problem (0:00–0:25)

**Show:** you on camera, or a single title slide.

> "Every PE firm runs the same play in the first 100 days: free up trapped
> cash. The biggest pool is almost always accounts receivable. Firms pay
> consultants six figures and wait two to three months for a working-capital
> diagnostic. I built an agent that does it in under a minute — and re-runs
> across every company in the portfolio."

## Shot 2 — The input (0:25–0:50)

**Show:** `data/ar_aging.csv` open in the editor.

> "The only input is an AR aging file — the open-invoice report any ERP
> exports in minutes. Here it's synthetic: 40 customers, about 200 invoices.
> Nothing else to integrate."

## Shot 3 — Run the agent (0:50–1:30)

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

## Shot 5 — The dashboard (1:45–2:35)

**Show:** browser — the Streamlit app. Click **Run the Working Capital Agent**,
let the status steps play. Walk **Act 1** (metric cards, aging chart,
narrative), then **Act 2**: the worklist table, then expand one email — pick
**Beacon Street Trading** (firm, escalatory) and one **Strategic** account to
contrast tone.

> "Same agent, with a dashboard. Act 1 is the diagnostic. Act 2 is the part a
> report can't do — a prioritized worklist of the ten accounts to call this
> week, and a drafted email for each one. Notice the tone shifts by account:
> firm and escalatory for a 90-day balance, warm for a strategic customer
> that's only days late. That's a collections team's week of work, ready to
> review and send."

## Shot 6 — Close (2:35–2:55)

**Show:** the README comparison table.

> "Six figures and three months becomes a few dollars and one minute — and
> because the input is a standard ERP export, the same agent drops onto every
> company in the portfolio. That's the difference between a consulting project
> and an agent."

---

## If anything goes wrong on camera

- App won't start: `python run_demo.py` alone tells the whole story — record
  that and skip the browser.
- Live API hiccup: unset `ANTHROPIC_API_KEY` and re-run; demo mode is instant
  and the output is identical.

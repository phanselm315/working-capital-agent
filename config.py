"""Central configuration for the Working Capital Agent.

Every tunable assumption lives here so a reviewer can see exactly what the
agent is doing and adjust it without reading the engine code.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEMO_CACHE_DIR = ROOT / "demo_cache"
AR_AGING_CSV = DATA_DIR / "ar_aging.csv"
CUSTOMERS_CSV = DATA_DIR / "customers.csv"
DEMO_CACHE_FILE = DEMO_CACHE_DIR / "responses.json"

# --- Reporting reference date -------------------------------------------
# The "as of" date the AR aging snapshot is measured against. All
# days-past-due math keys off this date. Fixed so the demo is reproducible.
AS_OF_DATE = date(2026, 5, 15)

# --- LLM -----------------------------------------------------------------
# Set MODEL to whatever current Claude model your account can access.
MODEL = os.environ.get("WCA_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# Demo mode serves pre-cached Claude outputs so the repo runs with no API
# key and no network. It turns ON automatically when no key is present and
# can be forced on with WCA_DEMO_MODE=1.
DEMO_MODE = (os.environ.get("WCA_DEMO_MODE", "").strip() == "1") or not ANTHROPIC_API_KEY

# --- Diagnostic thresholds ----------------------------------------------
# A well-run collections function lands a few days past stated terms.
# Target DSO = weighted-average payment terms + this buffer.
BEST_IN_CLASS_BUFFER_DAYS = 8

# Recoverability haircuts for the bottoms-up near-term cash estimate.
HAIRCUT_DISPUTED = 0.50   # disputed dollars: ~50% convert near-term
HAIRCUT_90_PLUS = 0.55    # 90+ day balances are heavily impaired
HAIRCUT_61_90 = 0.85      # 61-90 day balances modestly impaired

# --- Segmentation thresholds --------------------------------------------
STRATEGIC_TTM_REVENUE = 1_200_000  # >= this TTM revenue => Strategic account
CHRONIC_LATE_DAYS = 18             # avg days paid late at/above this => chronic
HIGH_RISK_PAST_DUE_DAYS = 61       # oldest past-due age that triggers escalation

# --- Remediation ---------------------------------------------------------
WORKLIST_SIZE = 10  # accounts in this week's prioritized collector worklist
FOLLOW_UP_DAYS = 5  # default days until the agent schedules a follow-up

# --- Approval queue ------------------------------------------------------
# Every email the agent drafts is staged for human review. Nothing is
# marked sendable until a reviewer approves it -- this is the human in the
# loop. "Edited" is a display tag, not a chosen state: it flags an approved
# email whose subject or body the reviewer changed before approving.
APPROVAL_STATES = ["Pending review", "Approved to send", "Held", "Rejected"]

# --- Fund / treasury rollup ---------------------------------------------
# The treasury view runs the diagnostic across every company in the fund
# and rolls it into one value bridge: a working-capital improvement becomes
# a recurring EBITDA lift, which -- valued at the EV/EBITDA multiple the
# asset was bought at -- becomes enterprise value created, and a MOIC lift
# on the fund's invested equity.
FUND_NAME = "Hadrian Capital Partners, Fund III"
PORTFOLIO_CSV = DATA_DIR / "portfolio.csv"
PORTFOLIO_DIR = DATA_DIR / "portfolio"

# EBITDA-lift model. A disciplined, always-on collections process recovers
# aged and disputed receivables that the status-quo process loses to
# write-off. Avoided bad-debt expense sits above the EBITDA line, so on an
# annual run-rate basis it is a recurring EBITDA improvement. This factor is
# the share of the agent-identified write-off-risk AR (disputed dollars plus
# the 90+ day bucket) that the process converts from a permanent write-off
# back into cash -- the net write-off avoided, not a gross write-off rate.
# It is the single biggest assumption in the treasury view -- tune it here.
BAD_DEBT_RECOVERY_UPLIFT = 0.35

# MOIC math. True -> value the EBITDA lift at the entry EV/EBITDA multiple
# (no multiple expansion; value creation is purely operational). This is the
# conservative, defensible default. The one-time working-capital cash
# release is valued separately, 1:1 against equity as it deleverages.
HOLD_ENTRY_MULTIPLE = True

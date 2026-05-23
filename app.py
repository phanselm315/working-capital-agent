"""Working Capital Agent -- Streamlit dashboard.

    streamlit run app.py

Act 1            the AR diagnostic.
Act 2            the prioritized collector worklist.
Approval Queue   human-in-the-loop review of every drafted email before send.
Treasury         the diagnostic rolled up across every company in the fund --
                 an EBITDA lift and an implied MOIC lift at the entry multiple.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from src import agent, approval, treasury

st.set_page_config(page_title="Working Capital Agent", layout="wide")


def usd(x) -> str:
    return f"${x:,.0f}"


def usdm(x) -> str:
    return f"${x / 1e6:,.1f}M"


def moic(x) -> str:
    return f"+{x:.2f}x"


def md_escape(s) -> str:
    """Escape '$' so Streamlit markdown does not read money figures as LaTeX math."""
    return str(s).replace("$", "\\$")


# --------------------------------------------------------------------- sidebar
with st.sidebar:
    st.subheader("Working Capital Agent")
    st.caption("An agentic AR diagnostic and collections workflow.")
    mode = "Demo mode -- cached Claude output" if config.DEMO_MODE else "Live -- Anthropic API"
    st.info(f"**{mode}**\n\nAR snapshot as of {config.AS_OF_DATE:%B %d, %Y}")
    st.markdown(
        "**Agent pipeline**\n"
        "1. Ingest AR aging + customer master\n"
        "2. Diagnose: DSO, aging, trapped cash\n"
        "3. Narrate: Claude writes the CFO brief\n"
        "4. Segment the customer book\n"
        "5. Prioritize the collector worklist\n"
        "6. Draft tone-matched outreach per account")
    st.markdown(
        "**Then**\n"
        "- Approval Queue: review every draft before send\n"
        "- Treasury: roll the diagnostic up across the fund")
    st.caption("All data is synthetic. Figures are illustrative.")


# ----------------------------------------------------------------------- intro
st.title("Working Capital Agent")
st.write(
    "Turns an accounts-receivable aging file into a CFO-grade diagnostic and a "
    "ready-to-send collections worklist -- the work a turnaround consultant is "
    "hired to do, run by an AI agent in seconds. Every draft passes a human "
    "approval gate, and the diagnostic rolls up across the whole fund.")

if "result" not in st.session_state:
    st.session_state.result = None

if st.button("Run the Working Capital Agent", type="primary"):
    with st.status("Running agent...", expanded=True) as status:
        st.session_state.result = agent.run(progress=status.write)
        status.update(label="Agent run complete.", state="complete", expanded=False)

result = st.session_state.result

tab1, tab2, tab3, tab4 = st.tabs([
    "Act 1  --  Diagnostic",
    "Act 2  --  Remediation",
    "Approval Queue",
    "Treasury  --  Fund View"])


# ====================================================================== Act 1
def render_act1(result):
    d = result.diagnostic
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total open AR", usd(d["total_ar"]))
    c2.metric("DSO", f"{d['dso']:.0f} days",
              f"{d['dso'] - d['target_dso']:+.0f} vs. target", delta_color="inverse")
    c3.metric("Past-due AR", usd(d["past_due_total"]),
              f"{d['past_due_pct'] * 100:.0f}% of AR", delta_color="off")
    c4.metric("Cash release opportunity", usd(d["cash_release_topdown"]),
              "close DSO to target", delta_color="off")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("AR aging")
        aging_df = pd.DataFrame(
            {"Open AR": [a["amount"] for a in d["aging"]]},
            index=[a["bucket"] for a in d["aging"]])
        st.bar_chart(aging_df, height=260)
    with right:
        st.subheader("Cash & risk")
        st.metric("Near-term collectible (past-due, risk-adjusted)",
                  usd(d["past_due_collectible"]))
        st.metric("Current AR likely to slip (payer history)",
                  usd(d["at_risk_current"]))
        st.metric("Disputed AR", f"{usd(d['dispute_amount'])}  ({d['dispute_count']} inv)")

    st.subheader("Diagnostic narrative")
    st.caption("Written by Claude from the figures above.")
    st.markdown(md_escape(result.narrative))

    st.subheader("Largest exposures")
    tc = pd.DataFrame(d["top_customers"])
    tc = pd.DataFrame({
        "Customer": tc["customer_name"],
        "Open AR": tc["open_balance"].map(usd),
        "Past due": tc["past_due_balance"].map(usd),
        "% of AR": (tc["pct_of_ar"] * 100).map(lambda v: f"{v:.1f}%"),
        "Oldest item": tc["oldest_dpd"].map(lambda v: f"{int(v)}d"),
    })
    st.dataframe(tc, hide_index=True, use_container_width=True)


# ====================================================================== Act 2
def render_act2(result):
    st.subheader("Customer segmentation")
    cols = st.columns(len(result.segment_summary))
    for col, s in zip(cols, result.segment_summary):
        col.metric(s["segment"], f"{s['customers']} accounts",
                   f"{usd(s['past_due_balance'])} past due", delta_color="off")

    st.subheader("This week's collector worklist")
    st.caption("Top accounts, ranked by past-due dollars, age and segment risk.")
    wl = result.worklist
    table = pd.DataFrame([{
        "#": w["rank"],
        "Customer": w["customer_name"],
        "Segment": w["segment"],
        "Past due": usd(w["past_due_balance"]),
        "Invoices": w["past_due_count"],
        "Oldest": f"{w['oldest_dpd']}d",
        "Recommended action": w["recommended_action"],
    } for w in wl])
    st.dataframe(table, hide_index=True, use_container_width=True)

    total = sum(w["past_due_balance"] for w in wl)
    st.info(md_escape(
        f"The agent drafted a tone-matched email for each of these "
        f"{len(wl)} accounts -- **{usd(total)}** of past-due exposure. "
        f"Every draft is staged in the **Approval Queue** tab for human "
        f"review before anything is sent."))


# ============================================================== Approval Queue
def render_approval(result):
    wl = result.worklist
    records = approval.build_queue(wl)

    st.subheader("Human-in-the-loop approval queue")
    st.caption("The agent drafts every email. Nothing is sendable until a "
               "reviewer approves it -- this is the human in the loop.")

    if "appr_sent" not in st.session_state:
        st.session_state.appr_sent = set()

    # Initialise per-email widget state once. Decisions persist across reruns.
    for r in records:
        cid = r["customer_id"]
        st.session_state.setdefault(f"appr_status_{cid}", approval.PENDING)
        st.session_state.setdefault(f"appr_subj_{cid}", r["original_subject"])
        st.session_state.setdefault(f"appr_body_{cid}", r["original_body"])
        st.session_state.setdefault(f"appr_note_{cid}", "")

    # Read the live decisions back out of widget state for the summary.
    decisions = []
    for r in records:
        cid = r["customer_id"]
        subj = st.session_state[f"appr_subj_{cid}"]
        body = st.session_state[f"appr_body_{cid}"]
        decisions.append({
            "record": r,
            "status": st.session_state[f"appr_status_{cid}"],
            "edited": approval.is_edited(subj, body, r),
            "sent": cid in st.session_state.appr_sent,
            "past_due_balance": r["past_due_balance"],
        })
    summ = approval.summarize(decisions)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Drafted", summ["total"])
    c2.metric("Pending review", summ["pending"])
    c3.metric("Approved to send", summ["approved"],
              f"{summ['edited']} edited" if summ["edited"] else None, delta_color="off")
    c4.metric("Held / rejected", summ["held"] + summ["rejected"])
    c5.metric("Past-due $ cleared to send", usd(summ["sendable_dollars"]))

    act1, act2 = st.columns([1, 3])
    with act1:
        send_clicked = st.button(
            f"Send {summ['approved']} approved email(s)",
            type="primary", disabled=summ["approved"] == 0)
    if send_clicked:
        for d in decisions:
            if d["status"] == approval.APPROVED:
                st.session_state.appr_sent.add(d["record"]["customer_id"])
        st.rerun()
    with act2:
        if summ["sent_count"]:
            st.success(f"{summ['sent_count']} email(s) marked sent. "
                       f"Simulated send -- the data is synthetic, nothing leaves this app.")
        else:
            st.caption("Approve drafts below, then send. Sending is simulated -- "
                       "no email is transmitted.")

    st.divider()

    for r in records:
        cid = r["customer_id"]
        status = st.session_state[f"appr_status_{cid}"]
        subj = st.session_state[f"appr_subj_{cid}"]
        body = st.session_state[f"appr_body_{cid}"]
        sent = cid in st.session_state.appr_sent
        edited = approval.is_edited(subj, body, r)
        badge = approval.display_status(status, edited, sent)
        head = (f"#{r['rank']}   {r['customer_name']}   --   "
                f"{usd(r['past_due_balance'])} past due   [{r['segment']}]   "
                f"::  {badge}")
        with st.expander(head, expanded=False):
            st.markdown(
                f"**To:** {r['contact_name']}  ({r['contact_email']})  &nbsp;|&nbsp;  "
                f"Tone: {r['tone']}  &nbsp;|&nbsp;  Action: {r['recommended_action']}")
            st.text_input("Subject", key=f"appr_subj_{cid}")
            st.text_area("Email body", key=f"appr_body_{cid}", height=240)
            d1, d2 = st.columns([1, 2])
            with d1:
                st.radio("Decision", config.APPROVAL_STATES, key=f"appr_status_{cid}")
            with d2:
                st.text_input("Reviewer note (optional)", key=f"appr_note_{cid}",
                              placeholder="e.g. checked with sales -- ok to send firm")
            if edited:
                st.caption("Draft edited from the agent's original.")
            if sent:
                st.success("Marked sent.")


# ============================================================ Treasury (fund)
def render_treasury():
    if "treasury" not in st.session_state:
        with st.spinner("Rolling the diagnostic up across the fund..."):
            st.session_state.treasury = treasury.run_treasury()
    t = st.session_state.treasury
    f = t["fund"]
    companies = t["companies"]

    st.subheader(f"{f['fund_name']}  --  working-capital rollup")
    st.caption(f"{f['company_count']} portfolio companies  ·  "
               f"AR snapshot as of {f['as_of_date']}  ·  "
               f"diagnostic re-run per company, deterministic")

    st.markdown(
        "**The value bridge.** Each company's working-capital diagnostic produces a "
        "recurring **EBITDA lift** -- a disciplined, always-on collections process "
        "recovers disputed and 90+ day receivables that the status-quo process loses "
        "to write-off, and that avoided bad-debt expense is recurring, above-the-line "
        "EBITDA. Valued at **the EV/EBITDA multiple each company was bought at**, the "
        "lift becomes enterprise value created. The one-time structural **cash "
        "release** deleverages 1:1. Both roll into a fund-level **MOIC lift**.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Portfolio companies", f["company_count"])
    c2.metric("Trapped working capital", usdm(f["total_cash_release"]),
              "one-time cash release", delta_color="off")
    c3.metric("Run-rate EBITDA lift", usdm(f["total_ebitda_lift"]),
              f"{f['total_ebitda_lift_pct'] * 100:.1f}% of fund EBITDA", delta_color="off")
    c4.metric("Implied EV created", usdm(f["total_ev_gain"]),
              f"at {f['blended_entry_multiple']:.1f}x blended", delta_color="off")
    c5.metric("Implied MOIC lift", moic(f["moic_lift_total"]),
              f"operating {moic(f['moic_lift_operating'])}", delta_color="off")

    st.caption(md_escape(
        f"MOIC lift on the fund's {usdm(f['invested_equity'])} invested equity: "
        f"operating {moic(f['moic_lift_operating'])} (EBITDA lift x entry multiple) + "
        f"deleveraging {moic(f['moic_lift_cash'])} (one-time cash release) = "
        f"{moic(f['moic_lift_total'])} total. Entry multiples held flat -- no multiple "
        f"expansion assumed; the lift is purely operational."))

    st.subheader("Per-company value bridge")
    rows = []
    for r in companies:
        c, d, b = r.company, r.diagnostic, r.bridge
        rows.append({
            "Company": c["company_name"],
            "Sector": c["sector"],
            "Entry mult": f"{c['entry_multiple']:.1f}x",
            "Fund invested": usd(c["fund_invested_equity"]),
            "DSO": f"{d['dso']:.0f}d",
            "Trapped cash": usd(b["cash_release"]),
            "EBITDA lift": usd(b["ebitda_lift"]),
            "EV gain": usd(b["ev_gain"]),
            "MOIC + (op)": moic(b["moic_lift_operating"]),
            "MOIC + (cash)": moic(b["moic_lift_cash"]),
            "MOIC + (total)": moic(b["moic_lift_total"]),
        })
    rows.append({
        "Company": "FUND TOTAL",
        "Sector": "",
        "Entry mult": f"{f['blended_entry_multiple']:.1f}x",
        "Fund invested": usd(f["invested_equity"]),
        "DSO": "",
        "Trapped cash": usd(f["total_cash_release"]),
        "EBITDA lift": usd(f["total_ebitda_lift"]),
        "EV gain": usd(f["total_ev_gain"]),
        "MOIC + (op)": moic(f["moic_lift_operating"]),
        "MOIC + (cash)": moic(f["moic_lift_cash"]),
        "MOIC + (total)": moic(f["moic_lift_total"]),
    })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.subheader("MOIC lift by company")
    st.caption("Operating lift (EBITDA x entry multiple) and deleveraging lift "
               "(one-time cash release), as incremental MOIC on invested equity.")
    chart_df = pd.DataFrame(
        {"Operating (EBITDA x multiple)": [r.bridge["moic_lift_operating"] for r in companies],
         "Deleveraging (cash release)": [r.bridge["moic_lift_cash"] for r in companies]},
        index=[r.company["company_name"] for r in companies])
    st.bar_chart(chart_df, height=320)

    st.caption(
        f"Assumptions (config.py): EBITDA lift = {config.BAD_DEBT_RECOVERY_UPLIFT:.0%} of "
        f"each company's write-off-risk AR (disputed + 90+ days). Entry multiples held "
        f"flat. All portfolio data is synthetic; figures are illustrative.")


# --------------------------------------------------------------------- render
with tab1:
    if result is None:
        st.info("Press **Run the Working Capital Agent** to analyze the AR book.")
    else:
        render_act1(result)

with tab2:
    if result is None:
        st.info("Press **Run the Working Capital Agent** to build the worklist.")
    else:
        render_act2(result)

with tab3:
    if result is None:
        st.info("Press **Run the Working Capital Agent** to draft outreach for review.")
    else:
        render_approval(result)

with tab4:
    render_treasury()

"""Working Capital Agent -- Streamlit dashboard.

    streamlit run app.py

Act 1 shows the AR diagnostic. Act 2 shows the prioritized collector
worklist and the outreach the agent drafted for each account.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from src import agent

st.set_page_config(page_title="Working Capital Agent", layout="wide")


def usd(x) -> str:
    return f"${x:,.0f}"


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
    st.caption("All data is synthetic. Figures are illustrative.")


# ------------------------------------------------------------------------ run
st.title("Working Capital Agent")
st.write(
    "Turns an accounts-receivable aging file into a CFO-grade diagnostic and a "
    "ready-to-send collections worklist -- the work a turnaround consultant is "
    "hired to do, run by an AI agent in seconds.")

if "result" not in st.session_state:
    st.session_state.result = None

if st.button("Run the Working Capital Agent", type="primary"):
    with st.status("Running agent...", expanded=True) as status:
        st.session_state.result = agent.run(progress=status.write)
        status.update(label="Agent run complete.", state="complete", expanded=False)

result = st.session_state.result
if result is None:
    st.info("Press **Run the Working Capital Agent** to analyze the AR book.")
    st.stop()

d = result.diagnostic
tab1, tab2 = st.tabs(["Act 1  --  Diagnostic", "Act 2  --  Remediation"])

# ---------------------------------------------------------------------- Act 1
with tab1:
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
    st.markdown(result.narrative)

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

# ---------------------------------------------------------------------- Act 2
with tab2:
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

    st.subheader("Drafted outreach")
    st.caption("One email per account, tone matched to segment -- drafted by Claude.")
    for w in wl:
        header = (f"#{w['rank']}   {w['customer_name']}   --   "
                  f"{usd(w['past_due_balance'])} past due   [{w['segment']}]")
        with st.expander(header):
            st.markdown(f"**To:** {w['contact_name']}  ({w['contact_email']})")
            st.markdown(f"**Subject:** {w['email_subject']}")
            st.text(w["email_body"])
            st.caption(f"Tone: {w['tone']}  |  Action: {w['recommended_action']}  "
                       f"|  Follow-up scheduled: {w['follow_up_date']}")

"""The Working Capital Agent -- orchestrates the full run.

Pipeline:
  1. ingest      load the AR aging snapshot + customer master
  2. diagnose    Act 1  -- deterministic working-capital metrics
  3. narrate     Act 1  -- Claude writes the CFO-facing diagnostic narrative
  4. segment     Act 2  -- rules-based customer segmentation
  5. prioritize  Act 2  -- build the top-N collector worklist
  6. draft       Act 2  -- Claude drafts tone-matched outreach per account

Deterministic math (steps 1, 2, 4, 5) is never delegated to the LLM, so the
numbers are exact and auditable. The LLM is used only for language (steps
3 and 6), where judgment and tone are the point.
"""
from __future__ import annotations

from dataclasses import dataclass

from src import diagnostic, ingest, llm, prompts, remediation


@dataclass
class AgentResult:
    diagnostic: dict
    narrative: str
    segment_summary: list
    worklist: list
    demo_mode: bool


def _split_email(text: str):
    """Split a 'Subject: ...\\n\\n<body>' response into (subject, body)."""
    body = text.strip()
    if body.lower().startswith("subject:"):
        first, _, rest = body.partition("\n")
        return first.split(":", 1)[1].strip(), rest.strip()
    return "", body


def run(progress=None) -> AgentResult:
    """Run the agent end to end. `progress` is an optional callback(str)."""
    def step(msg: str):
        if progress:
            progress(msg)

    step("Loading AR aging snapshot and customer master...")
    inv, cust = ingest.load_data()

    step("Act 1: running the working-capital diagnostic...")
    diag = diagnostic.run_diagnostic(inv, cust)

    step("Act 1: drafting the CFO diagnostic narrative...")
    narrative = llm.generate(
        "diagnostic_narrative",
        prompts.DIAGNOSTIC_SYSTEM,
        prompts.diagnostic_user(diag),
        max_tokens=700,
    )

    step("Act 2: segmenting the customer book...")
    segments = remediation.build_segments(inv, cust)
    seg_summary = remediation.segment_summary(segments)

    step("Act 2: prioritizing the collector worklist...")
    worklist = remediation.build_worklist(segments, inv)

    for item in worklist:
        step(f"Act 2: drafting outreach for {item['customer_name']}...")
        raw = llm.generate(
            f"email_{item['customer_id']}",
            prompts.EMAIL_SYSTEM,
            prompts.email_user(item),
            max_tokens=600,
        )
        subject, body = _split_email(raw)
        item["email_subject"] = subject
        item["email_body"] = body

    step("Done.")
    return AgentResult(
        diagnostic=diag,
        narrative=narrative,
        segment_summary=seg_summary,
        worklist=worklist,
        demo_mode=llm.is_demo_mode(),
    )

"""Approval queue -- the human-in-the-loop gate for agent-drafted outreach.

The agent drafts a collection email for every account on the worklist, but
nothing is sent until a person reviews it. This module models that review
lifecycle: each draft becomes a review record a reviewer can approve, hold
or reject -- and edit before approving. Only approved records are sendable.

The dashboard holds the live, per-email decisions in widget state; these
helpers build the records and turn a set of them into a queue summary the
reviewer can act on. No LLM is involved -- the gate is pure bookkeeping.
"""
from __future__ import annotations

import config

# Review states -- the choices a reviewer makes. (config.APPROVAL_STATES
# holds the same list so the dashboard and this module never drift apart.)
PENDING = "Pending review"
APPROVED = "Approved to send"
HELD = "Held"
REJECTED = "Rejected"

# Only an approved draft may actually be sent.
SENDABLE = (APPROVED,)

assert config.APPROVAL_STATES == [PENDING, APPROVED, HELD, REJECTED]


def new_record(item: dict) -> dict:
    """Build the initial review record for one worklist email."""
    subject = item.get("email_subject", "")
    body = item.get("email_body", "")
    return {
        "customer_id": item["customer_id"],
        "customer_name": item["customer_name"],
        "segment": item["segment"],
        "rank": item["rank"],
        "past_due_balance": item["past_due_balance"],
        "contact_name": item["contact_name"],
        "contact_email": item["contact_email"],
        "recommended_action": item["recommended_action"],
        "tone": item["tone"],
        "original_subject": subject,
        "original_body": body,
        "subject": subject,
        "body": body,
        "status": PENDING,
        "reviewer_note": "",
        "sent": False,
    }


def build_queue(worklist: list) -> list:
    """One review record per drafted email, in worklist priority order."""
    return [new_record(it) for it in worklist]


def is_edited(subject: str, body: str, record: dict) -> bool:
    """True if the reviewer changed the draft's subject or body."""
    return (subject.strip() != record["original_subject"].strip()
            or body.strip() != record["original_body"].strip())


def display_status(status: str, edited: bool, sent: bool) -> str:
    """The status label shown to the reviewer."""
    if sent:
        return "Sent"
    if status == APPROVED and edited:
        return "Approved (edited)"
    return status


def is_sendable(status: str) -> bool:
    return status in SENDABLE


def summarize(decisions: list) -> dict:
    """Aggregate the queue.

    `decisions` is a list of dicts with keys: status, edited, sent,
    past_due_balance -- the live state the dashboard pulls from its widgets.
    """
    s = {
        "total": len(decisions),
        "pending": 0, "approved": 0, "held": 0, "rejected": 0, "edited": 0,
        "sendable_count": 0, "sent_count": 0,
        "sendable_dollars": 0.0, "pending_dollars": 0.0,
        "past_due_total": sum(d["past_due_balance"] for d in decisions),
    }
    for d in decisions:
        if d["status"] == PENDING:
            s["pending"] += 1
            s["pending_dollars"] += d["past_due_balance"]
        elif d["status"] == APPROVED:
            s["approved"] += 1
            s["sendable_count"] += 1
            s["sendable_dollars"] += d["past_due_balance"]
            if d["edited"]:
                s["edited"] += 1
        elif d["status"] == HELD:
            s["held"] += 1
        elif d["status"] == REJECTED:
            s["rejected"] += 1
        if d["sent"]:
            s["sent_count"] += 1
    return s

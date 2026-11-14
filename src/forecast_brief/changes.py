"""What changed since last week's snapshot, and the pipeline waterfall.

The waterfall explains how this rep's open current-quarter pipeline moved from last
week's total to this week's total; it must add up exactly (checked with an assert).
"""
from .flags import RANK
from .load import fmt

CHANGE_ORDER = ["Won", "Lost", "Pushed out of quarter", "Downgraded", "Amount cut", "Reassigned",
                "Upgraded", "Amount increased", "Pulled into quarter", "New", "Stage moved"]
WATERFALL_KEYS = ["new", "pulled_in", "amount_change", "pushed_out", "lost", "won", "reassigned"]


def k(x):
    return f"{x // 1000}k"


def diff(rep, deals, snapshot, snap_date, in_q, stage_names, quarter_name):
    """Returns (changes, waterfall, last_week_total)."""
    current = {d["id"]: d for d in deals}
    last = {i: s for i, s in snapshot.items() if s["rep"] == rep}
    last_total = sum(s["amount"] for s in last.values() if in_q(s["close"]))
    wf = dict.fromkeys(WATERFALL_KEYS, 0)
    changes = []

    def add(kind, d, detail):
        changes.append(dict(type=kind, deal=d["name"], record_id=d["id"], amount=d["amount"], detail=detail))

    # deals that were open for this rep last week
    for i, s in last.items():
        was_q = in_q(s["close"])
        d = current.get(i)
        if d is None or d["rep"] != rep:
            add("Reassigned", s, "no longer with this rep" if d is None else f"now {d['rep']}")
            if was_q:
                wf["reassigned"] -= s["amount"]
            continue
        if d["status"] == "Won":
            add("Won", d, k(d["amount"]))
            if was_q:
                wf["won"] -= s["amount"]
            continue
        if d["status"] == "Lost":
            add("Lost", d, f"{k(d['amount'])} · {s['cat']}")
            if was_q:
                wf["lost"] -= s["amount"]
            continue
        now_q = in_q(d["close"])
        if was_q and not now_q:
            add(f"Pushed out of {quarter_name}", d, f"{k(s['amount'])} · {fmt(s['close'])} → {fmt(d['close'])}")
            wf["pushed_out"] -= s["amount"]
        elif now_q and not was_q:
            add(f"Pulled into {quarter_name}", d, f"{k(d['amount'])} · {fmt(s['close'])} → {fmt(d['close'])}")
            wf["pulled_in"] += d["amount"]
        if s["amount"] != d["amount"]:
            add("Amount cut" if d["amount"] < s["amount"] else "Amount increased", d,
                f"{k(s['amount'])} → {k(d['amount'])}")
            if was_q and now_q:
                wf["amount_change"] += d["amount"] - s["amount"]
        if s["cat"] != d["cat"] and s["cat"] in RANK and d["cat"] in RANK:
            add("Downgraded" if RANK[d["cat"]] < RANK[s["cat"]] else "Upgraded", d,
                f"{k(d['amount'])} · {s['cat']} → {d['cat']}")
        if s["stage"] is not None and s["stage"] != d["stage"]:
            add("Stage moved", d, f"{stage_names[s['stage']]} → {stage_names[d['stage']]}")

    # deals not in last week's snapshot for this rep
    for d in deals:
        if d["rep"] != rep or d["id"] in last:
            continue
        if d["status"] == "Open":
            add("New", d, f"{k(d['amount'])} · {d['cat']}")
            if in_q(d["close"]):
                wf["new"] += d["amount"]
        elif d["created"] and d["created"] > snap_date and d["close"] and d["close"] > snap_date:
            add(d["status"], d, f"{k(d['amount'])} (created and closed this week)")

    now_total = sum(d["amount"] for d in deals if d["rep"] == rep and d["status"] == "Open" and in_q(d["close"]))
    assert last_total + sum(wf.values()) == now_total, (rep, last_total, wf, now_total)

    def order(c):
        base = c["type"].replace(quarter_name, "quarter")
        return CHANGE_ORDER.index(base) if base in CHANGE_ORDER else len(CHANGE_ORDER)
    changes.sort(key=lambda c: (order(c), -c["amount"], c["deal"]))
    return changes, wf, last_total

"""Won-deal stage medians, 'won deals need', deal flags and the top 3 deals to discuss.

Rules (same as the answer-key generator, claude/v2_gen_data.py):
- Stage median = median days a WON deal spent in each stage (reps in the Quotas sheet only).
- Won deals need from stage i = sum of medians from stage i to signature.
- Flags only for open deals closing in the current quarter, plus overdue open deals.
"""
import statistics

from .load import fmt

RANK = {"Pipeline": 1, "Best case": 2, "Commit": 3}


def stage_medians(won_deals, n_stages):
    """Median days per stage; the last stage runs until the close date."""
    durations = [[] for _ in range(n_stages)]
    for d in won_deals:
        points = list(d["moved"]) + [d["close"]]
        for i in range(n_stages):
            if points[i] and points[i + 1]:
                durations[i].append((points[i + 1] - points[i]).days)
    medians = [statistics.median(x) if x else 0 for x in durations]
    need = [sum(medians[i:]) for i in range(n_stages)]
    return medians, need, [len(x) for x in durations]


def deal_flags(d, as_of, medians, need, settings, quarter_name):
    """List of (tag, text) for one open deal."""
    rules = settings["flagRules"]
    names = [s["name"] for s in settings["stages"]]
    default_cat = [s["defaultCategory"] for s in settings["stages"]]
    si = d["stage"]
    out = []

    if d["close"] < as_of:
        out.append(("Close date passed", f"{names[si]}. Close date {fmt(d['close'])} has passed"))

    # earlier stages that took much longer than won deals
    slow = []
    for k in range(si):
        a, b = d["moved"][k], d["moved"][k + 1]
        if a and b and (b - a).days > rules["earlierStageSlowFactor"] * medians[k]:
            slow.append((names[k], (b - a).days, medians[k]))
    if len(slow) >= rules["earlierStageSlowMinCount"] and d["cat"] in ("Commit", "Best case"):
        out.append((f"{d['cat']} stalled earlier", f"{names[si]}, {d['cat']}. Took " +
                    " and ".join(f"{n}d in {s} (+{n - m:g} vs median)" for s, n, m in slow)))

    if d["pushes"] >= rules["pushedMinCount"]:
        rates = settings["pushWinRates"]
        wr = rates.get(str(d["pushes"])) or rates.get(f"{rules['pushedMinCount'] + 1}+")
        out.append((f"Pushed {d['pushes']}×", f"{d['cat']}. Close date moved {d['pushes']} times, "
                    f"{d['slipped']} days in total. Deals pushed this often won {wr}"))
    elif d["slipped"] > rules["slippedMinDays"]:
        out.append((f"Slipped {d['slipped']}d", f"Close date moved {d['slipped']} days in total"))

    entered = d["moved"][si]
    over = None
    if entered:
        days_in = (as_of - entered).days
        over = days_in - medians[si]
    to_close = (d["close"] - as_of).days
    if 0 <= to_close < need[si]:
        txt = f"{names[si]}. {to_close}d to close date, won deals need ~{need[si]:.0f}d"
        if over is not None and over > 0:
            txt += f". {over:.0f}d over stage median"
        out.append((f"Unlikely to close in {quarter_name}", txt))
    elif over is not None and over > rules["stalledOverMedianFactor"] * medians[si]:
        out.append(("Stalled in stage", f"{names[si]}. {days_in}d in stage, {over:.0f}d over stage median"))

    if d["cat"] in RANK and RANK[d["cat"]] > RANK[default_cat[si]]:
        out.append(("Category above stage", f"{names[si]} called {d['cat']} (stage default: {default_cat[si]})"))
    return out


def top3(flagged, priority):
    """One deal per flag type in priority order, biggest amount first; current-quarter deals only.
    Fills up with the biggest remaining flagged deals if fewer than 3 types apply."""
    pool = sorted([f for f in flagged if not f["overdue"]], key=lambda f: (-f["amount"], f["deal"]))
    picked, ids = [], set()
    for p in priority:
        for f in pool:
            tag = next((t for t, _ in f["flags"] if p in t), None)
            if tag and f["record_id"] not in ids:
                picked.append(dict(f, reason=tag))
                ids.add(f["record_id"])
                break
        if len(picked) == 3:
            break
    for f in pool:
        if len(picked) == 3:
            break
        if f["record_id"] not in ids:
            picked.append(dict(f, reason=f["flags"][0][0]))
            ids.add(f["record_id"])
    return picked

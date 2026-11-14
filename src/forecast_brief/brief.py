"""Assemble everything the weekly email needs into one JSON-ready dict."""
from .changes import diff
from .flags import deal_flags, stage_medians, top3
from .load import fmt
from .writeback import hubspot_updates, snapshot_rows


def _status(x, thresholds):
    if x is None:
        return "quota reached"
    if x >= thresholds["green"]:
        return "green"
    return "amber" if x >= thresholds["amber"] else "red"


def build(deals, quotas, snap_date, snapshot, settings, as_of, test_mode, warnings=()):
    stage_names = [s["name"] for s in settings["stages"]]
    url = settings["dealUrl"]
    reps = set(quotas)
    warnings = list(warnings)
    if snap_date and snap_date >= as_of:
        raise ValueError(f"Snapshot {fmt(snap_date)} is not before the as-of date {fmt(as_of)}")

    # medians from won deals of the reps in the Quotas sheet only
    won_all = [d for d in deals if d["rep"] in reps and d["status"] == "Won" and d["close"] and d["close"] <= as_of]
    medians, need, counts = stage_medians(won_all, len(stage_names))

    for d in deals:
        if d["rep"] in reps and d["status"] == "Open":
            if d["close"] is None:
                warnings.append(f"{d['name']}: open deal without close date")
            if not d["moved"][d["stage"]]:
                warnings.append(f"{d['name']}: no 'Moved to {stage_names[d['stage']]}' date, stage-time flags skipped")
    deals = [d for d in deals if d["close"] is not None]

    def link(d):
        return url.format(id=d["id"])

    out_reps = []
    for rep in sorted(quotas):
        q = quotas[rep]
        qname = q["quarter"].split()[-1]                       # "2026 Q4" -> "Q4"
        in_q = lambda c, q=q: c is not None and q["start"] <= c <= q["end"]
        mine = [d for d in deals if d["rep"] == rep]

        won = sorted([d for d in mine if d["status"] == "Won" and in_q(d["close"]) and d["close"] <= as_of],
                     key=lambda d: (d["name"]))
        won_sum = sum(d["amount"] for d in won)
        remaining = q["quota"] - won_sum
        opn = [d for d in mine if d["status"] == "Open" and in_q(d["close"])]
        commit = [d for d in opn if d["cat"] == "Commit"]
        best = [d for d in opn if d["cat"] in ("Commit", "Best case")]
        cov = []
        for cat, group in [("Commit", commit), ("Best case", best), ("Pipeline", opn)]:
            amt = sum(d["amount"] for d in group)
            x = round(amt / remaining, 2) if remaining > 0 else None
            cov.append(dict(category=cat, amount=amt, x=x, deals=len(group),
                            status=_status(x, settings["coverageThresholds"][cat])))
        best_sum = cov[1]["amount"]
        top = sorted(best, key=lambda d: (-d["amount"], d["name"]))[:3]
        top_sum = sum(d["amount"] for d in top)
        share = top_sum / best_sum if best_sum else 0

        changes, wf, last_total = diff(rep, mine, snapshot, snap_date, in_q, stage_names, qname)

        flagged = []
        for d in sorted(mine, key=lambda x: (x["close"], x["name"])):
            if d["status"] == "Open" and (in_q(d["close"]) or d["close"] < as_of):
                f = deal_flags(d, as_of, medians, need, settings, qname)
                if f:
                    flagged.append(dict(deal=d["name"], record_id=d["id"], url=link(d), stage=stage_names[d["stage"]],
                                        category=d["cat"], amount=d["amount"], close=fmt(d["close"]),
                                        overdue=d["close"] < as_of, flags=[list(x) for x in f]))
        for c in changes:
            c["url"] = url.format(id=c["record_id"])

        out_reps.append(dict(
            rep=rep, quarter=q["quarter"], quarter_end=fmt(q["end"]), days_left=(q["end"] - as_of).days,
            quota=q["quota"], won=won_sum, bookings_pct=round(100 * won_sum / q["quota"]) if q["quota"] else None,
            won_deals=[dict(deal=d["name"], record_id=d["id"], url=link(d), amount=d["amount"], close=fmt(d["close"]))
                       for d in won],
            remaining=remaining, coverage=cov,
            expected_landing=won_sum + cov[0]["amount"],
            expected_landing_pct=round(100 * (won_sum + cov[0]["amount"]) / q["quota"]) if q["quota"] else None,
            concentration=dict(top3=[dict(deal=d["name"], record_id=d["id"], url=link(d), amount=d["amount"])
                                     for d in top],
                               pct=round(100 * share), flag=share > settings["concentrationShare"]),
            pipeline_last_week=last_total, pipeline_now=cov[2]["amount"],
            waterfall={k: v for k, v in wf.items() if v},
            changes=changes, flagged_deals=flagged,
            top3_to_discuss=top3(flagged, settings["top3Priority"]),
        ))

    first = quotas[sorted(quotas)[0]]
    return dict(
        as_of=fmt(as_of), test_mode=test_mode, subject_prefix="[TEST] " if test_mode else "",
        last_snapshot=fmt(snap_date), quarter=first["quarter"], quarter_end=fmt(first["end"]),
        days_left=(first["end"] - as_of).days,
        stage_medians=[dict(stage=s, median_days=m, won_deals_need_days=round(n), won_deals_counted=c)
                       for s, m, n, c in zip(stage_names, medians, need, counts)],
        reps=out_reps,
        snapshot=dict(filename=f"snapshot_{as_of.isoformat()}.csv",
                      rows=snapshot_rows(deals, reps, as_of, stage_names)),
        hubspot_updates=hubspot_updates(deals, reps, snapshot, as_of, settings),
        warnings=warnings,
    )

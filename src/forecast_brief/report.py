"""Print a brief in the same markdown layout as the answer key (claude/v2_answer_key.md),
so the two can be compared line by line."""


def _k(x):
    return f"{x / 1000:,.0f}k" if x < 1e6 else f"{x / 1e6:.2f}M"


def _g(x):
    return f"{x:g}"


def to_markdown(b):
    sm = b["stage_medians"]
    L = [f"# Answer key: forecast brief as of {b['as_of']} (last snapshot {b['last_snapshot']})", "",
         f"Days left in Q4: {b['days_left']}", "",
         "Stage medians of won deals (days): " + ", ".join(f"{s['stage']} {_g(s['median_days'])}" for s in sm), "",
         "Won deals need from entering a stage to signature: " +
         ", ".join(f"{s['stage']} ~{s['won_deals_need_days']}d" for s in sm), ""]
    for r in b["reps"]:
        c, bc, p = r["coverage"]
        conc = r["concentration"]
        L += [f"## {r['rep']}", "",
              f"- Quota {_k(r['quota'])}, won {_k(r['won'])} ({r['bookings_pct']}%: "
              f"{', '.join(w['deal'] for w in r['won_deals'])}), remaining {_k(r['remaining'])}",
              f"- Coverage on remaining: Commit {_k(c['amount'])} = {c['x']}×, Best case {_k(bc['amount'])} = {bc['x']}×, "
              f"Pipeline {_k(p['amount'])} = {p['x']}× ({p['deals']} deals)",
              f"- Expected landing (won + Commit): {_k(r['expected_landing'])} = {r['expected_landing_pct']}% of quota",
              f"- Top 3 of Best case: {conc['pct']}% ({', '.join(f'{t['deal']} {t['amount'] // 1000}k' for t in conc['top3'])}) "
              f"→ concentration flag: {'YES' if conc['flag'] else 'no'}",
              f"- Q4 pipeline {_k(r['pipeline_last_week'])} → {_k(r['pipeline_now'])}: " +
              ", ".join(f"{n} {v / 1000:+,.0f}k" for n, v in r["waterfall"].items()),
              "", "Changes since last week:", ""]
        L += [f"- {ch['type']}: {ch['deal']} ({ch['detail']})" for ch in r["changes"]]
        L += ["", "Flagged deals:", ""]
        for f in r["flagged_deals"]:
            L.append(f"- {f['deal']} ({f['amount'] // 1000}k, close {f['close']}): " +
                     " | ".join(f"**{t}** {x}" for t, x in f["flags"]))
        L.append("")
    return "\n".join(L)

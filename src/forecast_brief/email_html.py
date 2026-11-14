"""Render brief.json as the weekly HTML email.

Gmail rules (tested 14.11.2026): the Gmail connector strips every CSS background /
background-color at send time, so ALL fills use the HTML bgcolor attribute on table/td.
Layout uses nested tables (no float, no flex, no grid). Borders, text colours, bold and
border-radius survive.
"""
from html import escape

# colour pairs: (fill, text)
GREEN = ("#EAF3DE", "#3B6D11")
AMBER = ("#FAEEDA", "#854F0B")
RED = ("#FCEBEB", "#A32D2D")
GREY = ("#F1EFE8", "#5F5E5A")
STATUS = {"green": GREEN, "amber": AMBER, "red": RED, "quota reached": GREEN}
PAGE, CARD, BORDER, TEXT, MUTED, LINK = "#F5F4F0", "#FFFFFF", "#E5E3DC", "#2C2C2A", "#73726C", "#185FA5"
BAR_FILL, BAR_EMPTY = "#639922", "#E5E3DC"
FONT = "font-family:Arial,Helvetica,sans-serif;"


def k(x):
    return f"{x / 1000:,.0f}k" if abs(x) < 1e6 else f"{x / 1e6:.2f}M"


def tag_colour(tag):
    if tag.startswith(("Unlikely", "Close date passed")):
        return RED
    if tag.startswith("Category above"):
        return GREY
    return AMBER                     # stalled earlier, Pushed, Slipped, Stalled in stage


CHANGE_COLOUR = {"Won": GREEN, "Upgraded": GREEN, "Amount increased": GREEN, "Lost": RED, "Downgraded": AMBER,
                 "Amount cut": AMBER, "Reassigned": GREY, "New": GREY, "Stage moved": GREY}


def change_colour(kind):
    if kind.startswith("Pushed out"):
        return RED
    if kind.startswith("Pulled into"):
        return GREEN
    return CHANGE_COLOUR.get(kind, GREY)


def link(text, url, bold=True):
    w = "font-weight:bold;" if bold else ""
    return f'<a href="{escape(url)}" style="color:{LINK};text-decoration:underline;{w}">{escape(text)}</a>'


def pill(text, colour):
    fill, fg = colour
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table;'
            f'margin:0 4px 4px 0;"><tr><td bgcolor="{fill}" style="{FONT}font-size:11px;color:{fg};'
            f'padding:2px 7px;border-radius:4px;white-space:nowrap;">{escape(text)}</td></tr></table>')


def section(title):
    return (f'<tr><td style="{FONT}font-size:12px;color:{MUTED};padding:18px 0 6px 0;text-transform:uppercase;'
            f'letter-spacing:0.5px;">{escape(title)}</td></tr>')


def progress_bar(pct):
    pct = max(0, min(100, pct or 0))
    filled = f'<td width="{pct}%" bgcolor="{BAR_FILL}" height="8" style="font-size:0;line-height:0;">&nbsp;</td>' if pct else ""
    empty = (f'<td width="{100 - pct}%" bgcolor="{BAR_EMPTY}" height="8" style="font-size:0;line-height:0;">&nbsp;</td>'
             if pct < 100 else "")
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-radius:4px;"><tr>{filled}{empty}</tr></table>')


def coverage_tile(c, remaining):
    fill, fg = STATUS[c["status"]]
    right = f'{c["x"]:.2f}×' if c["x"] is not None else "quota reached"
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin-bottom:4px;border-radius:6px;"><tr>'
            f'<td bgcolor="{fill}" style="{FONT}font-size:13px;color:{fg};padding:6px 10px;border-radius:6px 0 0 6px;">'
            f'{escape(c["category"])} {k(c["amount"])} <span style="font-size:11px;">· {c["deals"]} deals</span></td>'
            f'<td bgcolor="{fill}" align="right" style="{FONT}font-size:17px;font-weight:bold;color:{fg};'
            f'padding:6px 10px;border-radius:0 6px 6px 0;white-space:nowrap;">{right}</td></tr></table>')


def flag_lines(flags):
    pills = "".join(pill(t, tag_colour(t)) for t, _ in flags)
    texts = "".join(f'<div style="{FONT}font-size:12px;color:{MUTED};padding-top:2px;">'
                    f'<b style="color:{TEXT};">{escape(t)}:</b> {escape(x)}</div>' for t, x in flags)
    return pills + texts


def deal_meta(f):
    return f'{k(f["amount"])} · {escape(f["stage"])} · {escape(f["category"] or "no category")} · close {f["close"]}'


def rep_block(r, points):
    c0 = r["coverage"]
    rows = [f'<tr><td style="{FONT}font-size:20px;font-weight:bold;color:{TEXT};padding:0 0 2px 0;">{escape(r["rep"])}</td></tr>',
            f'<tr><td style="{FONT}font-size:12px;color:{MUTED};padding-bottom:10px;">'
            f'Quota {k(r["quota"])} · {r["quarter"]} · {r["days_left"]} days left</td></tr>']

    # bookings to target
    won_names = ", ".join(link(w["deal"].split(" - ")[0], w["url"], bold=False) for w in r["won_deals"]) or "none yet"
    rows += [section("Bookings to target"),
             f'<tr><td style="{FONT}font-size:14px;color:{TEXT};padding-bottom:6px;"><span style="font-size:22px;'
             f'font-weight:bold;">{k(r["won"])}</span> of {k(r["quota"])} won ({r["bookings_pct"]}%) · '
             f'{k(max(r["remaining"], 0))} to go</td></tr>',
             f'<tr><td style="padding-bottom:4px;">{progress_bar(r["bookings_pct"])}</td></tr>',
             f'<tr><td style="{FONT}font-size:12px;color:{MUTED};">Won: {won_names}</td></tr>']

    # coverage on remaining target
    rows += [section(f'Coverage on remaining {k(max(r["remaining"], 0))}')]
    rows += [f'<tr><td>{coverage_tile(c, r["remaining"])}</td></tr>' for c in c0]
    rows.append(f'<tr><td style="{FONT}font-size:13px;color:{TEXT};padding-top:6px;">Expected landing (won + Commit): '
                f'<b>{k(r["expected_landing"])}</b> = {r["expected_landing_pct"]}% of quota</td></tr>')
    conc = r["concentration"]
    if conc["flag"]:
        names = ", ".join(f'{link(t["deal"].split(" - ")[0], t["url"], bold=False)} {k(t["amount"])}' for t in conc["top3"])
        rows.append(f'<tr><td style="padding-top:6px;"><table role="presentation" width="100%" cellpadding="0" '
                    f'cellspacing="0" border="0"><tr><td bgcolor="{AMBER[0]}" style="{FONT}font-size:12px;color:{AMBER[1]};'
                    f'padding:6px 10px;border-radius:6px;"><b>Concentration:</b> top 3 deals are {conc["pct"]}% of '
                    f'Best case ({names})</td></tr></table></td></tr>')

    # what changed since last week
    wf = ", ".join(f'{n.replace("_", " ")} {v / 1000:+,.0f}k' for n, v in r["waterfall"].items())
    rows += [section("What changed since last week"),
             f'<tr><td style="{FONT}font-size:12px;color:{MUTED};padding-bottom:6px;">{r["quarter"].split()[-1]} pipeline '
             f'{k(r["pipeline_last_week"])} → {k(r["pipeline_now"])}{": " + wf if wf else ""}</td></tr>']
    if r["changes"]:
        ch = "".join(
            f'<tr><td width="120" valign="top" style="padding:5px 8px 5px 0;white-space:nowrap;border-top:1px solid {BORDER};">'
            f'{pill(c["type"], change_colour(c["type"]))}</td>'
            f'<td valign="top" style="{FONT}font-size:13px;color:{TEXT};padding:5px 0;border-top:1px solid {BORDER};">'
            f'{link(c["deal"].split(" - ")[0], c["url"])} <span style="color:{MUTED};">{escape(c["deal"].split(" - ", 1)[-1])}'
            f' · {escape(c["detail"])}</span></td></tr>' for c in r["changes"])
        rows.append(f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{ch}'
                    f'</table></td></tr>')
    else:
        rows.append(f'<tr><td style="{FONT}font-size:13px;color:{MUTED};">No changes.</td></tr>')

    # top 3 deals to discuss
    if r["top3_to_discuss"]:
        rows.append(section("Top 3 deals to discuss"))
        for t in r["top3_to_discuss"]:
            rows.append(f'<tr><td style="padding:6px 0 8px 0;border-top:1px solid {BORDER};">'
                        f'<div style="{FONT}font-size:14px;color:{TEXT};padding-bottom:4px;">{link(t["deal"], t["url"])} '
                        f'<span style="font-size:12px;color:{MUTED};">{deal_meta(t)}</span></div>'
                        f'{flag_lines(t["flags"])}</td></tr>')

    # talking points (written by Claude from the flags; numbers come from the script)
    if points:
        items = "".join(f'<li style="padding-bottom:4px;">{escape(p)}</li>' for p in points)
        rows += [section("Talking points"),
                 f'<tr><td style="{FONT}font-size:13px;color:{TEXT};"><ul style="margin:0;padding-left:18px;">'
                 f'{items}</ul></td></tr>']

    inner = "".join(rows)
    return (f'<tr><td style="padding:0 0 16px 0;"><table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" border="0" style="border:1px solid {BORDER};border-radius:10px;"><tr>'
            f'<td bgcolor="{CARD}" style="padding:18px 20px;border-radius:10px;"><table role="presentation" '
            f'width="100%" cellpadding="0" cellspacing="0" border="0">{inner}</table></td></tr></table></td></tr>')


def appendix(b):
    rows = []
    for r in b["reps"]:
        if not r["flagged_deals"]:
            continue
        rows.append(f'<tr><td style="{FONT}font-size:14px;font-weight:bold;color:{TEXT};padding:12px 0 4px 0;">'
                    f'{escape(r["rep"])} · {len(r["flagged_deals"])} flagged deals</td></tr>')
        for f in r["flagged_deals"]:
            rows.append(f'<tr><td style="padding:6px 0 8px 0;border-top:1px solid {BORDER};">'
                        f'<div style="{FONT}font-size:13px;color:{TEXT};padding-bottom:4px;">{link(f["deal"], f["url"])} '
                        f'<span style="font-size:12px;color:{MUTED};">{deal_meta(f)}</span></div>'
                        f'{flag_lines(f["flags"])}</td></tr>')
    if not rows:
        return ""
    inner = "".join(rows)
    return (f'<tr><td style="padding:0 0 16px 0;"><table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" border="0" style="border:1px solid {BORDER};border-radius:10px;"><tr>'
            f'<td bgcolor="{CARD}" style="padding:18px 20px;border-radius:10px;"><table role="presentation" '
            f'width="100%" cellpadding="0" cellspacing="0" border="0">{section("Appendix: all flagged deals")}{inner}'
            f'</table></td></tr></table></td></tr>')


def subject(b):
    return f'{b["subject_prefix"]}Forecast brief {b["as_of"]} · {b["quarter"].split()[-1]}: {b["days_left"]} days left'


def render(b, talking_points=None):
    """b = brief dict; talking_points = {rep name: [str, ...]} (optional)."""
    talking_points = talking_points or {}
    need = " · ".join(f'{s["stage"]} ~{s["won_deals_need_days"]}d' for s in b["stage_medians"])
    won_n = max(s["won_deals_counted"] for s in b["stage_medians"])
    test = (f'<tr><td style="padding:0 0 12px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0"><tr><td bgcolor="{AMBER[0]}" style="{FONT}font-size:12px;color:{AMBER[1]};padding:8px 12px;'
            f'border-radius:6px;"><b>TEST MODE.</b> Nothing was written to HubSpot or Drive.</td></tr></table>'
            f'</td></tr>') if b["test_mode"] else ""
    header = (f'<tr><td style="padding:4px 0 14px 0;"><div style="{FONT}font-size:22px;font-weight:bold;color:{TEXT};">'
              f'Forecast brief</div><div style="{FONT}font-size:13px;color:{MUTED};padding-top:2px;">'
              f'As of {b["as_of"]} · {b["quarter"]} ends {b["quarter_end"]} · {b["days_left"]} days left · '
              f'compared with {b["last_snapshot"]}</div></td></tr>')
    reps = "".join(rep_block(r, talking_points.get(r["rep"])) for r in b["reps"])
    footer = (f'<tr><td style="{FONT}font-size:11px;color:{MUTED};padding:4px 4px 0 4px;line-height:1.5;">'
              f'Won deals need, from entering a stage to signature (median of {won_n} won deals): {need}.<br>'
              f'Coverage colours: Commit green ≥1.0×, amber 0.7–1.0×; Best case green ≥1.5×, amber 1.0–1.5×; '
              f'Pipeline green ≥3×, amber 2–3×; red below. Best case includes Commit.<br>'
              f'Numbers are calculated from HubSpot by a fixed script; talking points are written by Claude from '
              f'the flags.</td></tr>')
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{escape(subject(b))}</title></head>'
            f'<body style="margin:0;padding:0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" bgcolor="{PAGE}"><tr><td align="center" bgcolor="{PAGE}" style="padding:20px 10px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;">'
            f'{test}{header}{reps}{appendix(b)}{footer}</table></td></tr></table></body></html>')


def main(argv=None):
    """python3 render_email.py --brief brief.json [--talking-points tp.json] --html email.html"""
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Render brief.json as the HTML email")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--talking-points", help='JSON: {"Anna Keller": ["...", "..."], ...}')
    ap.add_argument("--html", default="email.html")
    a = ap.parse_args(argv)
    with open(a.brief, encoding="utf-8") as fh:
        b = json.load(fh)
    tp = None
    if a.talking_points:
        with open(a.talking_points, encoding="utf-8") as fh:
            tp = json.load(fh)
    with open(a.html, "w", encoding="utf-8") as fh:
        fh.write(render(b, tp))
    print(subject(b))
    return 0

"""Render brief.json as the weekly HTML email (layout = agreed mockup v3).

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
BLUE = ("#E6F1FB", "#185FA5")
STATUS = {"green": GREEN, "amber": AMBER, "red": RED, "quota reached": GREEN}
BAR = {"green": "#639922", "amber": "#BA7517", "red": "#E24B4A"}
PAGE, CARD, BORDER, STRONG, TEXT, MUTED, LINK = "#F5F4F0", "#FFFFFF", "#E5E3DC", "#C9C7BE", "#2C2C2A", "#73726C", "#185FA5"
BAR_EMPTY = "#E5E3DC"
FONT = "font-family:Arial,Helvetica,sans-serif;"
TABLE = 'role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
LANDING_GREEN, LANDING_AMBER = 85, 70          # bookings bar colour by expected landing % of quota


def k(x):
    return f"{x / 1000:,.0f}k" if abs(x) < 1e6 else f"{x / 1e6:.2f}M"


def name(deal):
    """'Lemaniatech - Planning suite' -> 'Lemaniatech · Planning suite'"""
    return deal.replace(" - ", " · ", 1)


def short_date(dmy):
    return dmy[:5]                                   # 18.12.2026 -> 18.12


def tag_colour(tag):
    if tag.startswith(("Commit stalled", "Best case stalled", "Pushed", "Close date passed")):
        return RED
    if tag.startswith(("Unlikely", "Category above", "Slipped", "Stalled")):
        return AMBER
    return GREY


def change_colour(kind):
    if kind in ("Won", "Upgraded", "Amount increased") or kind.startswith("Pulled into"):
        return GREEN
    if kind == "Lost" or kind.startswith("Pushed out"):
        return RED
    return GREY


def landing_status(pct):
    return "green" if pct >= LANDING_GREEN else "amber" if pct >= LANDING_AMBER else "red"


def link(text, url, bold=True):
    w = "font-weight:bold;" if bold else ""
    return f'<a href="{escape(url)}" style="color:{LINK};text-decoration:underline;{w}">{escape(text)}</a>'


def pill(text, colour):
    fill, fg = colour
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table;'
            f'vertical-align:middle;margin:0 4px 2px 0;"><tr><td bgcolor="{fill}" style="{FONT}font-size:11px;'
            f'color:{fg};padding:1px 6px;border-radius:4px;white-space:nowrap;">{escape(text)}</td></tr></table>')


def sec(title):
    return f'<div style="{FONT}font-size:12px;color:{MUTED};padding:14px 0 4px 0;">{escape(title)}</div>'


def box(html, colour, size=13):
    fill, fg = colour
    return (f'<table {TABLE} style="margin-top:8px;"><tr><td bgcolor="{fill}" style="{FONT}font-size:{size}px;'
            f'color:{fg};padding:7px 10px;border-radius:6px;">{html}</td></tr></table>')


def progress_bar(pct, status):
    pct = max(0, min(100, pct or 0))
    cells = ""
    if pct:
        cells += f'<td width="{pct}%" bgcolor="{BAR[status]}" height="8" style="font-size:0;line-height:0;">&nbsp;</td>'
    if pct < 100:
        cells += f'<td width="{100 - pct}%" bgcolor="{BAR_EMPTY}" height="8" style="font-size:0;line-height:0;">&nbsp;</td>'
    return f'<table {TABLE}><tr>{cells}</tr></table>'


def coverage_tiles(cov):
    """Three single-line tiles side by side: label left, multiple right."""
    cells = []
    for i, c in enumerate(cov):
        fill, fg = STATUS[c["status"]]
        right = f'{c["x"]:.2f}×' if c["x"] is not None else "met"
        pad = "0 4px 0 0" if i == 0 else "0 0 0 4px" if i == 2 else "0 2px"
        cells.append(
            f'<td width="33%" valign="top" style="padding:{pad};"><table {TABLE}><tr>'
            f'<td bgcolor="{fill}" style="{FONT}font-size:12px;color:{fg};padding:5px 0 5px 10px;'
            f'border-radius:6px 0 0 6px;">{escape(c["category"])} {k(c["amount"])}</td>'
            f'<td bgcolor="{fill}" align="right" style="{FONT}font-size:17px;font-weight:bold;color:{fg};'
            f'padding:5px 10px 5px 4px;border-radius:0 6px 6px 0;white-space:nowrap;">{right}</td>'
            f'</tr></table></td>')
    return f'<table {TABLE}><tr>{"".join(cells)}</tr></table>'


def changes_grid(changes):
    """Change items in two columns to save vertical space."""
    items = [f'{pill(c["type"], change_colour(c["type"]))} {link(name(c["deal"]), c["url"])} '
             f'<span style="color:{MUTED};">{escape(c["detail"])}</span>' for c in changes]
    rows = []
    for i in range(0, len(items), 2):
        pair = items[i:i + 2] + [""] * (2 - len(items[i:i + 2]))
        rows.append("<tr>" + "".join(
            f'<td width="50%" valign="top" style="{FONT}font-size:13px;color:{TEXT};'
            f'padding:4px {"12px" if j == 0 else "0"} 4px 0;">{it}</td>' for j, it in enumerate(pair)) + "</tr>")
    return f'<table {TABLE}>{"".join(rows)}</table>'


def reason_lines(flags):
    if len(flags) == 1:
        return f'<div style="color:{MUTED};font-size:12px;padding-top:2px;">{escape(flags[0][1])}</div>'
    return "".join(f'<div style="color:{MUTED};font-size:12px;padding-top:2px;">{escape(t)}: {escape(x)}</div>'
                   for t, x in flags)


def top_deals(top):
    head = (f'<tr><td style="{FONT}font-size:12px;color:{MUTED};padding:0 0 2px 0;">Deal and reason</td>'
            f'<td width="60" align="right" style="{FONT}font-size:12px;color:{MUTED};">Amount</td>'
            f'<td width="50" align="right" style="{FONT}font-size:12px;color:{MUTED};">Close</td></tr>')
    rows = []
    for t in top:
        tags = "".join(pill(tag, tag_colour(tag)) for tag, _ in t["flags"])
        cell = f'border-top:1px solid {BORDER};padding:7px 0;{FONT}font-size:13px;color:{TEXT};'
        rows.append(f'<tr><td valign="top" style="{cell}padding-right:8px;">{link(name(t["deal"]), t["url"])} '
                    f'{tags}{reason_lines(t["flags"])}</td>'
                    f'<td valign="top" align="right" style="{cell}">{k(t["amount"])}</td>'
                    f'<td valign="top" align="right" style="{cell}">{short_date(t["close"])}</td></tr>')
    return f'<table {TABLE}>{head}{"".join(rows)}</table>'


def talking_box(points):
    items = "".join(f'<div style="padding-top:3px;">{i}. {escape(p)}</div>' for i, p in enumerate(points, 1))
    return box(f'<div style="font-weight:bold;">Talking points for the call</div>{items}', BLUE)


def rep_block(r, points):
    first = r["rep"].split()[0]
    conc = r["concentration"]
    landing_pct = r["expected_landing_pct"] or 0
    html = [
        f'<div style="border-top:1px solid {STRONG};margin-top:16px;padding-top:14px;">',
        f'<table {TABLE}><tr><td style="{FONT}font-size:16px;font-weight:bold;color:{TEXT};">{escape(r["rep"])}</td>'
        f'<td align="right" style="{FONT}font-size:12px;color:{MUTED};">Quota {k(r["quota"])}</td></tr></table>',
        f'<table {TABLE} style="margin:8px 0 4px 0;"><tr><td style="{FONT}font-size:13px;color:{TEXT};">'
        f'Bookings to target: <b>{k(r["won"])} · {r["bookings_pct"]}%</b></td>'
        f'<td align="right" style="{FONT}font-size:13px;color:{MUTED};">{k(max(r["remaining"], 0))} remaining</td>'
        f'</tr></table>',
        progress_bar(r["bookings_pct"], landing_status(landing_pct)),
        sec(f'Coverage on remaining {k(max(r["remaining"], 0))}'),
        coverage_tiles(r["coverage"]),
    ]
    landing = f'Expected landing: {k(r["expected_landing"])} · {landing_pct}% of quota'
    if not conc["flag"]:
        landing += f' · top 3 deals {conc["pct"]}% of Best case'
    html.append(f'<div style="{FONT}font-size:13px;color:{MUTED};padding-top:6px;">{landing}</div>')
    if conc["flag"]:
        best = r["coverage"][1]["amount"]
        top_sum = sum(t["amount"] for t in conc["top3"])
        names = ", ".join(f'{escape(t["deal"].split(" - ")[0])} {k(t["amount"])}' for t in conc["top3"])
        html.append(box(f'<b>Deal concentration:</b> top 3 deals are {conc["pct"]}% of Best case '
                        f'({k(top_sum)} of {k(best)}): {names}', RED))

    html += [sec("What changed since last week"),
             f'<div style="{FONT}font-size:13px;color:{TEXT};padding-bottom:4px;">{r["quarter"].split()[-1]} pipeline '
             f'{k(r["pipeline_last_week"])} → <b>{k(r["pipeline_now"])}</b></div>',
             changes_grid(r["changes"]) if r["changes"]
             else f'<div style="{FONT}font-size:13px;color:{MUTED};">No changes.</div>']

    if r["top3_to_discuss"]:
        html += [sec("Top deals to discuss"), top_deals(r["top3_to_discuss"])]
    if r["flagged_deals"]:
        html.append(f'<div style="{FONT}font-size:12px;color:{MUTED};padding-top:4px;">All '
                    f'{len(r["flagged_deals"])} flagged deals for {escape(first)} are in the appendix below.</div>')
    if points:
        html.append(talking_box(points))
    html.append("</div>")
    return "".join(html)


def appendix(b):
    parts = []
    for r in b["reps"]:
        if not r["flagged_deals"]:
            continue
        rows = "".join(
            f'<tr><td valign="top" style="{FONT}font-size:13px;padding:6px 8px 6px 0;border-top:1px solid {BORDER};">'
            f'{link(name(f["deal"]), f["url"], bold=False)}</td>'
            f'<td width="150" valign="top" style="{FONT}font-size:12px;color:{MUTED};padding:6px 8px 6px 0;'
            f'border-top:1px solid {BORDER};">{escape(", ".join(t for t, _ in f["flags"]))}</td>'
            f'<td width="50" valign="top" align="right" style="{FONT}font-size:13px;color:{TEXT};padding:6px 0;'
            f'border-top:1px solid {BORDER};">{k(f["amount"])}</td></tr>' for f in r["flagged_deals"])
        parts.append(sec(f'{r["rep"]} · {len(r["flagged_deals"])} deals') + f'<table {TABLE}>{rows}</table>')
    if not parts:
        return ""
    return (f'<div style="border-top:1px solid {STRONG};margin-top:18px;padding-top:14px;">'
            f'<div style="{FONT}font-size:16px;font-weight:bold;color:{TEXT};">Appendix: all flagged deals</div>'
            f'{"".join(parts)}</div>')


def team_summary(b):
    quota = sum(r["quota"] for r in b["reps"])
    won = sum(r["won"] for r in b["reps"])
    landing = sum(r["expected_landing"] for r in b["reps"])
    q = b["quarter"].split()[-1]
    stats = [(f"Team quota {q}", k(quota), ""), ("Won so far", k(won), f'{round(100 * won / quota)}%' if quota else ""),
             ("Remaining target", k(max(quota - won, 0)), ""), ("Days left", str(b["days_left"]), "")]
    cells = "".join(
        f'<td width="25%" valign="top" style="padding-right:8px;"><div style="{FONT}font-size:12px;color:{MUTED};">{lbl}</div>'
        f'<div style="{FONT}font-size:22px;color:{TEXT};">{val} '
        f'<span style="font-size:13px;color:{MUTED};">{extra}</span></div></td>' for lbl, val, extra in stats)
    return (f'<table {TABLE}><tr>{cells}</tr></table>'
            f'<div style="{FONT}font-size:13px;color:{MUTED};padding-top:6px;">Expected landing (won + Commit): '
            f'{k(landing)} · {round(100 * landing / quota) if quota else 0}% of quota</div>')


def subject(b):
    return f'{b["subject_prefix"]}Forecast brief {b["as_of"]} · {b["quarter"].split()[-1]}: {b["days_left"]} days left'


def render(b, talking_points=None):
    """b = brief dict; talking_points = {rep name: [str, ...]} (optional)."""
    talking_points = talking_points or {}
    q = b["quarter"].split()[-1]
    need = ", ".join(f'{s["stage"]} ~{s["won_deals_need_days"]}d' for s in b["stage_medians"])
    test = box("<b>TEST MODE.</b> Nothing was written to HubSpot or Drive.", AMBER, 12) if b["test_mode"] else ""
    header = (f'<div style="{FONT}font-size:13px;color:{MUTED};padding:8px 4px 10px 4px;line-height:1.7;">'
              f'<b style="color:{TEXT};">{q} forecast brief · week of {b["as_of"]}</b><br>'
              f'Compared with {b["last_snapshot"]}</div>')
    reps = "".join(rep_block(r, talking_points.get(r["rep"])) for r in b["reps"])
    footer = (f'<div style="{FONT}font-size:11px;color:{MUTED};margin-top:16px;border-top:1px solid {BORDER};'
              f'padding-top:8px;line-height:1.5;">Coverage: Commit green ≥1.0×, amber 0.7–1.0×. Best case green ≥1.5×, '
              f'amber 1.0–1.5×. Pipeline green ≥3×, amber 2–3×. Red below. Best case includes Commit. Concentration '
              f'flag when top 3 deals exceed 60% of Best case. Won deals need from entering a stage to signature: '
              f'{need} (medians from won deals, recalculated each run). Numbers by rules, talking points by Claude. '
              f'Deal names link to HubSpot.</div>')
    card = (f'<table {TABLE} style="border:1px solid {BORDER};border-radius:12px;"><tr><td bgcolor="{CARD}" '
            f'style="padding:16px 20px;border-radius:12px;">{team_summary(b)}{reps}{appendix(b)}{footer}'
            f'</td></tr></table>')
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{escape(subject(b))}</title></head>'
            f'<body style="margin:0;padding:0;"><table {TABLE} bgcolor="{PAGE}"><tr><td align="center" bgcolor="{PAGE}" '
            f'style="padding:16px 8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="max-width:680px;"><tr><td>{test}{header}{card}'
            f'</td></tr></table></td></tr></table></body></html>')


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

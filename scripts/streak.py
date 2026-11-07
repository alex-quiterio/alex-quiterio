"""Render a contribution streak card as SVG, styled to match the 3D night skyline.

Usage: GITHUB_TOKEN=... python3 scripts/streak.py <username> <output.svg>
Uses only the standard library.
"""

import datetime as dt
import json
import os
import sys
import urllib.request

API = "https://api.github.com/graphql"

BG = "#00000f"
FG = "#eeeeff"
WEAK = "#aaaaaa"
STRONG = "rgb(255,200,55)"
BLUE = "#1f6feb"
CYAN = "#39c5ff"


def graphql(query, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "profile-streak-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]


def contribution_days(login):
    created = graphql(
        "query($login:String!){user(login:$login){createdAt}}", {"login": login}
    )["user"]["createdAt"]
    start = dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    days = {}
    query = """
    query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from, to:$to) {
          contributionCalendar { weeks { contributionDays { date contributionCount } } }
        }
      }
    }"""
    cursor = start
    while cursor < now:
        end = min(cursor + dt.timedelta(days=365), now)
        data = graphql(
            query, {"login": login, "from": cursor.isoformat(), "to": end.isoformat()}
        )
        weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            for day in week["contributionDays"]:
                days[dt.date.fromisoformat(day["date"])] = day["contributionCount"]
        cursor = end
    return days


def streaks(days):
    today = max(days)
    # Today with no contributions yet doesn't break the streak.
    day = today if days.get(today, 0) else today - dt.timedelta(days=1)
    current_end = day
    current = 0
    while days.get(day, 0) > 0:
        current += 1
        day -= dt.timedelta(days=1)
    current_start = day + dt.timedelta(days=1)

    longest, run, run_start = 0, 0, None
    longest_range = (None, None)
    for d in sorted(days):
        if days[d] > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest, longest_range = run, (run_start, d)
        else:
            run = 0
    return {
        "total": sum(days.values()),
        "first": min(d for d in days if days[d] > 0) if any(days.values()) else today,
        "today": today,
        "current": current,
        "current_range": (current_start, current_end) if current else (None, None),
        "longest": longest,
        "longest_range": longest_range,
    }


def fmt(d, with_year=False):
    if d is None:
        return ""
    return d.strftime("%b %-d, %Y" if with_year else "%b %-d")


def span(a, b):
    if a is None:
        return "no active streak"
    if a == b:
        return fmt(a, True)
    return f"{fmt(a, a.year != b.year)} – {fmt(b, True)}"


def render(stats):
    total = f"{stats['total']:,}"
    total_sub = f"{fmt(stats['first'], True)} – present"
    cur = stats["current"]
    cur_sub = span(*stats["current_range"])
    longest = stats["longest"]
    longest_sub = span(*stats["longest_range"])
    # Stars scattered behind the card, fixed so the image only changes with the numbers.
    stars = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{FG}" opacity="{o}"/>'
        for x, y, r, o in [
            (60, 40, 1.2, 0.6), (180, 210, 1, 0.4), (330, 30, 1.4, 0.7),
            (520, 220, 1, 0.5), (760, 26, 1.2, 0.5), (910, 214, 1.4, 0.6),
            (1080, 48, 1, 0.4), (1220, 200, 1.2, 0.7), (1240, 30, 1, 0.5),
            (450, 120, 0.8, 0.3), (830, 130, 0.8, 0.3), (40, 190, 1, 0.4),
        ]
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="250" viewBox="0 0 1280 250">
<title>Contribution streak: {cur} days current, {longest} days longest, {total} total</title>
<style>
  * {{ font-family: "Ubuntu", "Helvetica", "Arial", sans-serif; }}
  .num {{ font-size: 54px; font-weight: 700; fill: {FG}; }}
  .big {{ font-size: 64px; font-weight: 700; fill: {STRONG}; }}
  .label {{ font-size: 22px; fill: {FG}; letter-spacing: 1px; }}
  .sub {{ font-size: 17px; fill: {WEAK}; }}
  .ring {{ animation: draw 1.6s ease-out forwards; }}
  @keyframes draw {{ from {{ stroke-dashoffset: 534; }} to {{ stroke-dashoffset: 0; }} }}
</style>
<defs>
  <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{CYAN}"/>
    <stop offset="1" stop-color="{BLUE}"/>
  </linearGradient>
  <radialGradient id="glow">
    <stop offset="0" stop-color="{BLUE}" stop-opacity="0.35"/>
    <stop offset="1" stop-color="{BLUE}" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="1280" height="250" rx="12" fill="{BG}"/>
{stars}
<line x1="427" y1="50" x2="427" y2="200" stroke="{WEAK}" stroke-opacity="0.25"/>
<line x1="853" y1="50" x2="853" y2="200" stroke="{WEAK}" stroke-opacity="0.25"/>

<g text-anchor="middle">
  <text x="213" y="112" class="num">{total}</text>
  <text x="213" y="152" class="label">Total contributions</text>
  <text x="213" y="182" class="sub">{total_sub}</text>
</g>

<g text-anchor="middle">
  <circle cx="640" cy="98" r="110" fill="url(#glow)"/>
  <circle cx="640" cy="98" r="85" fill="none" stroke="{BLUE}" stroke-opacity="0.2" stroke-width="8"/>
  <circle class="ring" cx="640" cy="98" r="85" fill="none" stroke="url(#ringGrad)" stroke-width="8"
          stroke-linecap="round" stroke-dasharray="534" transform="rotate(-90 640 98)"/>
  <text x="640" y="118" class="big">{cur}</text>
  <text x="640" y="215" class="label" fill="{STRONG}" style="fill:{STRONG}">Current streak</text>
  <text x="640" y="240" class="sub">{cur_sub}</text>
</g>

<g text-anchor="middle">
  <text x="1067" y="112" class="num">{longest}</text>
  <text x="1067" y="152" class="label">Longest streak</text>
  <text x="1067" y="182" class="sub">{longest_sub}</text>
</g>
</svg>
"""


def main():
    login, out = sys.argv[1], sys.argv[2]
    stats = streaks(contribution_days(login))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print(
        f"current={stats['current']} longest={stats['longest']} total={stats['total']}"
    )


if __name__ == "__main__":
    main()

"""Render a contribution streak card as SVG, styled as a night-sky vigil: gold on deep indigo.

Usage: GITHUB_TOKEN=... python3 scripts/streak.py <username> <output.svg>
Uses only the standard library.
"""

import datetime as dt
import json
import math
import os
import sys
import urllib.request

API = "https://api.github.com/graphql"

BG = "#0a0618"
FG = "#f3ecd8"
WEAK = "#a99fc9"
GOLD = "#e8c872"
VIOLET = "#8b6cf0"
INDIGO = "#3b2a8c"


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


def rune(kind, x, y):
    """Elder Futhark runes drawn as strokes, so they render without a rune font."""
    w, h = 20, 38
    paths = {
        # Fehu: fortune and abundance
        "fehu": f"M0,{h} L0,0 M0,{h * 0.3} L{w},0 M0,{h * 0.62} L{w},{h * 0.32}",
        # Uruz: strength and vitality
        "uruz": f"M0,{h} L0,0 L{w},{h * 0.3} L{w},{h}",
    }
    return (
        f'<path d="{paths[kind]}" transform="translate({x - w / 2},{y})" fill="none" stroke="{GOLD}" '
        f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def render(stats):
    total = f"{stats['total']:,}"
    total_sub = f"since {fmt(stats['first'], True)}"
    cur = stats["current"]
    cur_sub = span(*stats["current_range"])
    longest = stats["longest"]
    longest_sub = span(*stats["longest_range"])
    # Twelve spokes like a zodiac wheel; positions are fixed so the image only changes with the numbers.
    cx, cy = 640, 92
    spokes = "".join(
        f'<line x1="{cx + 68 * math.cos(math.radians(a)):.1f}" y1="{cy + 68 * math.sin(math.radians(a)):.1f}" '
        f'x2="{cx + (82 if a % 90 == 0 else 76) * math.cos(math.radians(a)):.1f}" '
        f'y2="{cy + (82 if a % 90 == 0 else 76) * math.sin(math.radians(a)):.1f}" '
        f'stroke="{GOLD}" stroke-width="{2 if a % 90 == 0 else 1}" stroke-opacity="0.8"/>'
        for a in range(0, 360, 30)
    )
    # Two interlaced triangles make a hexagram inside the wheel.
    def tri(offset):
        pts = " ".join(
            f"{cx + 52 * math.cos(math.radians(offset + k * 120)):.1f},{cy + 52 * math.sin(math.radians(offset + k * 120)):.1f}"
            for k in range(3)
        )
        return f'<polygon points="{pts}" fill="none" stroke="{VIOLET}" stroke-opacity="0.55" stroke-width="1.2"/>'
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
<title>Vigil: {cur} days current, {longest} days longest, {total} offerings in total</title>
<style>
  * {{ font-family: "Cormorant Garamond", "Palatino", "Georgia", serif; }}
  .num {{ font-size: 56px; font-weight: 600; fill: {FG}; }}
  .big {{ font-size: 56px; font-weight: 600; fill: {GOLD}; }}
  .label {{ font-size: 21px; fill: {GOLD}; letter-spacing: 5px; text-transform: uppercase; }}
  .sub {{ font-size: 18px; font-style: italic; fill: {WEAK}; }}
  .turn {{ transform-origin: {cx}px {cy}px; animation: turn 120s linear infinite; }}
  .breath {{ animation: breath 6s ease-in-out infinite; }}
  @keyframes turn {{ to {{ transform: rotate(360deg); }} }}
  @keyframes breath {{ 0%, 100% {{ opacity: 0.55; }} 50% {{ opacity: 1; }} }}
  @media (prefers-reduced-motion: reduce) {{ .turn, .breath {{ animation: none; }} }}
</style>
<defs>
  <radialGradient id="aura">
    <stop offset="0" stop-color="{VIOLET}" stop-opacity="0.45"/>
    <stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{GOLD}" stop-opacity="0"/>
    <stop offset="0.5" stop-color="{GOLD}" stop-opacity="0.7"/>
    <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="1280" height="250" rx="12" fill="{BG}"/>
<rect width="1280" height="250" rx="12" fill="none" stroke="{INDIGO}" stroke-width="2"/>
{stars}

<g text-anchor="middle">
  {rune("fehu", 213, 22)}
  <text x="213" y="124" class="num">{total}</text>
  <text x="213" y="160" class="label">Offerings</text>
  <text x="213" y="190" class="sub">{total_sub}</text>
</g>

<g text-anchor="middle">
  <circle class="breath" cx="{cx}" cy="{cy}" r="100" fill="url(#aura)"/>
  <circle cx="{cx}" cy="{cy}" r="62" fill="none" stroke="{INDIGO}" stroke-width="2"/>
  <circle cx="{cx}" cy="{cy}" r="57" fill="none" stroke="{GOLD}" stroke-opacity="0.5" stroke-width="1"/>
  <g class="turn">{spokes}</g>
  {tri(-90)}{tri(90)}
  <text x="{cx}" y="{cy + 22}" class="big">{cur}</text>
  <text x="{cx}" y="{cy + 118}" class="label">Current vigil</text>
  <text x="{cx}" y="{cy + 142}" class="sub" style="font-size:16px">{cur_sub}</text>
</g>

<g text-anchor="middle">
  {rune("uruz", 1067, 22)}
  <text x="1067" y="124" class="num">{longest}</text>
  <text x="1067" y="160" class="label">Longest vigil</text>
  <text x="1067" y="190" class="sub">{longest_sub}</text>
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

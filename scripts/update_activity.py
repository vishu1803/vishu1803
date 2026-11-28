#!/usr/bin/env python3
"""Generate the profile's local GitHub contribution calendar SVG."""

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
USERNAME = "vishu1803"
SVG_NS = "http://www.w3.org/2000/svg"


def fetch_calendar(start: date, end: date) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Set GITHUB_TOKEN to a GitHub token before running this script.")

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        },
    }
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-activity-svg",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("errors"):
        messages = "; ".join(error.get("message", "Unknown GraphQL error") for error in result["errors"])
        raise RuntimeError(f"GitHub GraphQL request failed: {messages}")

    try:
        return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (KeyError, TypeError) as error:
        raise RuntimeError("GitHub returned no contribution calendar for this user.") from error


def color_for(count: int) -> str:
    if count == 0:
        return "#21262d"
    if count <= 2:
        return "#0e4429"
    if count <= 5:
        return "#006d32"
    if count <= 9:
        return "#26a641"
    return "#39d353"


def render_svg(calendar: dict) -> str:
    width, height = 900, 236
    grid_x, grid_y = 146, 92
    cell, step = 11, 13
    weeks = calendar["weeks"]
    parts = [
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '  <rect x="1" y="1" width="898" height="234" rx="14" fill="#161b22" stroke="#30363d" stroke-width="2"/>',
        '  <text x="28" y="37" fill="#f0f6fc" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="20" font-weight="700">GitHub activity</text>',
        f'  <text x="28" y="61" fill="#8b949e" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="13">{calendar["totalContributions"]} public contributions in the last year</text>',
    ]

    seen_months = set()
    for week_index, week in enumerate(weeks):
        x = grid_x + week_index * step
        days = week["contributionDays"]
        for day in days:
            day_date = date.fromisoformat(day["date"])
            year_month = (day_date.year, day_date.month)
            if day_date.day == 1 and year_month not in seen_months:
                parts.append(
                    f'  <text x="{x}" y="82" fill="#8b949e" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11">{day_date.strftime("%b")}</text>'
                )
                seen_months.add(year_month)

            y = grid_y + day["weekday"] * step
            count = day["contributionCount"]
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color_for(count)}"/>'
            )

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = grid_y + weekday * step + 9
        parts.append(
            f'  <text x="105" y="{y}" fill="#8b949e" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10">{label}</text>'
        )

    legend_y = 207
    parts.append(
        f'  <text x="{grid_x}" y="{legend_y}" fill="#8b949e" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11">Less</text>'
    )
    for index, color in enumerate(("#21262d", "#0e4429", "#006d32", "#26a641", "#39d353")):
        x = grid_x + 39 + index * 15
        parts.append(f'  <rect x="{x}" y="{legend_y - 10}" width="10" height="10" rx="2" fill="{color}"/>')
    parts.append(
        f'  <text x="{grid_x + 120}" y="{legend_y}" fill="#8b949e" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11">More</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=364)
    calendar = fetch_calendar(start, end)
    output = ROOT / "assets" / "activity.svg"
    output.write_text(render_svg(calendar), encoding="utf-8")
    print(f"Updated {output.relative_to(ROOT)} with {calendar['totalContributions']} contributions.")


if __name__ == "__main__":
    main()

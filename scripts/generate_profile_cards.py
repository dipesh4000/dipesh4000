from __future__ import annotations

import base64
import datetime as dt
import html
import json
import math
import os
import re
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USERNAME = "dipesh4000"
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

BG = "#161616"
BORDER = "#2a2a2a"
TEXT = "#f3f4f6"
MUTED = "#8b8b8b"
SUBTLE = "#666666"
GREEN = ["#24292f", "#0e4429", "#006d32", "#26a641", "#39d353"]
BAR = "#2b2b2b"


def get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "dipesh4000-profile-dashboard"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def svg_doc(width: int, height: int, inner: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="{BG}" stroke="{BORDER}"/>
  {inner}
</svg>\n'''


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fetch_codio() -> dict:
    url = "https://raw.githubusercontent.com/dipesh4000/portfolio-site/main/public/data/codio-stats.json"
    try:
        return json.loads(get(url).decode("utf-8"))
    except Exception:
        return {
            "dsa": {"total": 326, "easy": 125, "medium": 145, "hard": 19, "other": 37},
            "maxStreak": 24,
            "submissions": 656,
            "totalActiveDays": 181,
            "currentStreak": 4,
            "contest": {"rating": 1585, "contests": 14},
            "github": {"stars": 28, "pullRequests": 9, "issues": 5, "contributions": 849},
        }


def fetch_avatar_data_uri() -> str:
    try:
        raw = get(f"https://github.com/{USERNAME}.png?size=512")
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    except Exception:
        return ""


def generate_about() -> None:
    avatar = fetch_avatar_data_uri()
    image = "" if not avatar else f'<image href="{avatar}" x="24" y="24" width="220" height="220" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatarClip)"/>'
    fallback = '<text x="134" y="145" fill="#d1d5db" text-anchor="middle" font-size="54" font-weight="700">DK</text>' if not image else ""

    text = '''<text x="278" y="56" fill="#707070" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11">dipesh4000 / README.md</text>
    <text x="278" y="92" fill="#f5f5f5" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="28" font-weight="700">Howdy!</text>
    <text x="278" y="122" fill="#c6c6c6" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13">I'm a developer focused on AI/ML, GenAI, data and backend systems.</text>
    <text x="278" y="146" fill="#c6c6c6" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13">I like turning ideas into practical tools and learning by building.</text>
    <text x="278" y="170" fill="#c6c6c6" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13">Currently exploring FastAPI, Django, Python, React/Next.js, and modern AI stacks.</text>
    <text x="278" y="194" fill="#c6c6c6" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13">My focus is strong fundamentals, useful projects, and clean engineering.</text>
    <line x1="278" y1="214" x2="838" y2="214" stroke="#2b2b2b"/>
    <text x="278" y="242" fill="#989898" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11">CURRENTLY BUILDING</text>
    <text x="278" y="266" fill="#f0f0f0" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13">AI/ML projects • backend systems • data-driven developer tooling</text>'''

    inner = '''<defs>
      <clipPath id="avatarClip"><rect x="24" y="24" width="220" height="220" rx="14"/></clipPath>
    </defs>
    <rect x="24" y="24" width="220" height="220" rx="14" fill="#202020"/>
    ''' + image + fallback + text
    (ASSETS / "about.svg").write_text(svg_doc(870, 290, inner), encoding="utf-8")


def parse_contributions(days_html: str) -> tuple[dict[dt.date, tuple[int, int]], int]:
    # GitHub's contribution calendar exposes data-date, data-level and data-count.
    cells = re.findall(
        r'<td[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d+)"[^>]*?(?:data-count="(\d+)")?[^>]*>',
        days_html,
    )
    out: dict[dt.date, tuple[int, int]] = {}
    total = 0
    for date_s, level_s, count_s in cells:
        day = dt.date.fromisoformat(date_s)
        count = int(count_s or 0)
        out[day] = (int(level_s), count)
        total += count
    return out, total


def fetch_contributions() -> tuple[dict[dt.date, tuple[int, int]], int]:
    today = dt.date.today()
    start = today - dt.timedelta(days=365)
    qs = urllib.parse.urlencode({"from": start.isoformat(), "to": today.isoformat()})
    url = f"https://github.com/users/{USERNAME}/contributions?{qs}"
    raw = get(url, headers={"User-Agent": "dipesh4000-profile-dashboard", "Accept": "text/html"})
    cells, total = parse_contributions(raw.decode("utf-8", errors="ignore"))
    if not cells:
        raise RuntimeError("Could not parse GitHub contribution calendar")
    return cells, total


def month_positions(start: dt.date, end: dt.date, x0: int, col_w: int) -> list[tuple[str, int]]:
    positions: list[tuple[str, int]] = []
    cur = dt.date(start.year, start.month, 1)
    while cur <= end:
        sunday = cur - dt.timedelta(days=(cur.weekday() + 1) % 7)
        col = (sunday - start).days // 7
        if 0 <= col <= 60:
            positions.append((cur.strftime("%b"), x0 + col * col_w))
        if cur.month == 12:
            cur = dt.date(cur.year + 1, 1, 1)
        else:
            cur = dt.date(cur.year, cur.month + 1, 1)
    return positions


def generate_contributions() -> None:
    try:
        cells, total = fetch_contributions()
    except Exception as exc:
        previous = ASSETS / "contributions.svg"
        if previous.exists():
            print(f"Contribution refresh failed; keeping previous file: {exc}")
            return
        today = dt.date.today()
        cells = {today: (0, 0)}
        total = 0
        print(f"Contribution refresh unavailable: {exc}")

    min_day = min(cells)
    max_day = max(cells)
    start = min_day - dt.timedelta(days=(min_day.weekday() + 1) % 7)
    end = max_day + dt.timedelta(days=(6 - ((max_day.weekday() + 1) % 7)) % 7)

    x0, y0 = 34, 92
    size, gap = 11, 3
    col_w = size + gap
    inner = []
    inner += [
        f'<text x="34" y="48" fill="{TEXT}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="23" font-weight="700">{total:,} contributions in the last year</text>',
        f'<rect x="752" y="28" width="82" height="34" rx="8" fill="#202020" stroke="#2d2d2d"/>',
        f'<text x="767" y="50" fill="#c6c6c6" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12">{dt.date.today().year}</text>',
        f'<text x="821" y="50" fill="#6f6f6f" text-anchor="end" font-size="10">⌄</text>',
    ]
    for label, x in month_positions(start, end, x0, col_w):
        inner.append(f'<text x="{x}" y="76" fill="#777" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10">{label}</text>')

    days_by_col: dict[int, list[tuple[dt.date, int]]] = {}
    for day, (level, _) in cells.items():
        col = (day - start).days // 7
        row = (day.weekday() + 1) % 7
        days_by_col.setdefault(col, []).append((day, row))
    for col, entries in days_by_col.items():
        for day, row in entries:
            level = cells[day][0]
            color = GREEN[min(max(level, 0), 4)]
            x = x0 + col * col_w
            y = y0 + row * col_w
            inner.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2.5" fill="{color}"><title>{day.isoformat()}: {cells[day][1]} contributions</title></rect>')

    # Legend
    lx = 664
    inner.append(f'<text x="{lx - 58}" y="204" fill="#767676" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10">Less</text>')
    for i, color in enumerate(GREEN):
        inner.append(f'<rect x="{lx + i * 14}" y="195" width="10" height="10" rx="2" fill="{color}"/>')
    inner.append(f'<text x="{lx + 5 * 14 + 4}" y="204" fill="#767676" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10">More</text>')

    (ASSETS / "contributions.svg").write_text(svg_doc(870, 235, "\n".join(inner)), encoding="utf-8")


def fetch_repos() -> list[dict]:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"User-Agent": "dipesh4000-profile-dashboard", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    raw = get(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated",
        headers=headers,
    )
    repos = json.loads(raw.decode("utf-8"))
    repos = [r for r in repos if not r.get("fork") and not r.get("archived") and r.get("name") != USERNAME]
    repos.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0), r.get("updated_at", "")), reverse=True)
    return repos[:4]


def compact(text_value: str, width: int = 48) -> str:
    text_value = (text_value or "No description provided.").replace("\n", " ").strip()
    return textwrap.shorten(text_value, width=width, placeholder="…")


def generate_popular_repos() -> None:
    try:
        repos = fetch_repos()
    except Exception as exc:
        print(f"Repository refresh failed: {exc}")
        repos = []

    inner = [
        f'<text x="28" y="42" fill="{TEXT}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="21" font-weight="700">Popular repositories</text>',
        f'<text x="205" y="42" fill="#777" font-size="11">⌄</text>',
    ]

    positions = [(28, 58), (312, 58), (28, 200), (312, 200)]
    for i, (x, y) in enumerate(positions):
        repo = repos[i] if i < len(repos) else None
        inner.append(f'<rect x="{x}" y="{y}" width="260" height="124" rx="12" fill="#202020" stroke="#2c2c2c"/>')
        if repo:
            name = esc(repo.get("name", "unknown"))
            language = esc(repo.get("language") or "—")
            desc = esc(compact(repo.get("description") or "", 44))
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            inner += [
                f'<text x="{x + 18}" y="{y + 28}" fill="#f2f2f2" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="14" font-weight="600">▱ {name}</text>',
                f'<text x="{x + 18}" y="{y + 50}" fill="#9a9a9a" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12">{desc}</text>',
                f'<text x="{x + 18}" y="{y + 74}" fill="#a7a7a7" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11">★ {stars:,}   ⑂ {forks:,}</text>',
                f'<text x="{x + 18}" y="{y + 100}" fill="#6f6f6f" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10">{language}</text>',
            ]
        else:
            inner.append(f'<text x="{x + 18}" y="{y + 28}" fill="#666" font-size="13">Repository data unavailable</text>')

    (ASSETS / "popular-repos.svg").write_text(svg_doc(590, 350, "\n".join(inner)), encoding="utf-8")


def generate_achievements() -> None:
    data = fetch_codio()
    dsa = data.get("dsa", {})
    github = data.get("github", {})
    contest = data.get("contest", {})
    items = [
        ("DSA", f"{dsa.get('total', 0)} solved", "◆"),
        ("STREAK", f"{data.get('maxStreak', 0)} days max", "↯"),
        ("CONTEST", f"{contest.get('contests', 0)} contests", "★"),
        ("ACTIVE", f"{data.get('totalActiveDays', 0)} days", "●"),
        ("STARS", f"{github.get('stars', 0)} stars", "✦"),
        ("PULL REQUESTS", f"{github.get('pullRequests', 0)} PRs", "⌁"),
    ]
    inner = [
        f'<text x="24" y="38" fill="{TEXT}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="17" font-weight="700">Achievements</text>',
        f'<text x="24" y="56" fill="#6d6d6d" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10">selected milestones</text>',
    ]
    for i, (label, value, icon) in enumerate(items):
        row, col = divmod(i, 2)
        x = 24 + col * 134
        y = 78 + row * 64
        inner += [
            f'<circle cx="{x + 18}" cy="{y + 18}" r="15" fill="#222" stroke="#363636"/>',
            f'<text x="{x + 18}" y="{y + 23}" fill="#d5d5d5" font-size="15" text-anchor="middle">{icon}</text>',
            f'<text x="{x + 42}" y="{y + 15}" fill="#8e8e8e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="8">{esc(label)}</text>',
            f'<text x="{x + 42}" y="{y + 33}" fill="#f1f1f1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11">{esc(value)}</text>',
        ]
    inner.append(f'<line x1="24" y1="278" x2="292" y2="278" stroke="#2b2b2b"/>')
    inner.append(f'<text x="24" y="300" fill="#686868" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="9">data source: Codolio JSON + GitHub API</text>')
    (ASSETS / "achievements.svg").write_text(svg_doc(320, 328, "\n".join(inner)), encoding="utf-8")


def main() -> None:
    generate_about()
    generate_contributions()
    generate_popular_repos()
    generate_achievements()
    print("Profile dashboard cards refreshed.")


if __name__ == "__main__":
    main()

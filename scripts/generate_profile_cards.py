from __future__ import annotations

import base64
import datetime as dt
import html
import json
import os
import re
import textwrap
from pathlib import Path
import json as _json
import urllib.request as _urllib_request
from urllib.parse import urlencode

# =========================================================
# Configuration
# =========================================================

USERNAME = "dipesh4000"
ROOT = Path(__file__).resolve().parents[1] if (Path(__file__).resolve().parents[1] / "assets").exists() else Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

CODIO_STATS_URL = (
    "https://raw.githubusercontent.com/"
    "dipesh4000/portfolio-site/main/"
    "public/data/codio-stats.json"
)

# Set GENERATE_DSA=false in the new profile workflow when your existing
# Codolio workflow already owns assets/dsa-stats.svg.
GENERATE_DSA = os.getenv("GENERATE_DSA", "true").lower() == "true"

OUTPUTS = {
    "about": ASSETS / "about.svg",
    "dsa": ASSETS / "dsa-stats.svg",
    "contributions": ASSETS / "contributions.svg",
    "repos": ASSETS / "popular-repos.svg",
    "achievements": ASSETS / "achievements.svg",
}

# =========================================================
# Theme
# =========================================================

BG = "#111111"
CARD = "#171717"
CARD_2 = "#202020"
BORDER = "#2B2B2B"
PRIMARY = "#F2F2F2"
SECONDARY = "#8B8B8B"
MUTED = "#666666"

GREEN = "#39D353"
GREEN_DARK = "#196C2E"
MEDIUM = "#D4A72C"
HARD = "#F85149"
OTHER = "#6E7681"
CONTRIBUTION_COLORS = ["#24292f", "#0e4429", "#006d32", "#26a641", "#39d353"]

UA = {"User-Agent": "dipesh4000-github-profile-dashboard"}

# =========================================================
# Generic helpers
# =========================================================


class _Response:
    """Minimal response wrapper around urllib so the rest of the code is unchanged."""

    def __init__(self, data: bytes, status: int) -> None:
        self._data = data
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP error {self.status}")

    @property
    def text(self) -> str:
        return self._data.decode("utf-8", errors="replace")

    @property
    def content(self) -> bytes:
        return self._data

    def json(self) -> object:
        return _json.loads(self._data)


def get(url: str, *, headers: dict | None = None, timeout: int = 20) -> _Response:
    merged = dict(UA)
    if headers:
        merged.update(headers)
    req = _urllib_request.Request(url, headers=merged)
    with _urllib_request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        status = resp.status
    return _Response(data, status)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_number(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def percentage(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, (value / total) * 100.0))


def svg_text(
    text: object,
    x: float,
    y: float,
    size: float = 14,
    fill: str = PRIMARY,
    weight: int = 400,
    anchor: str = "start",
    family: str = "Arial, Helvetica, sans-serif",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" '
        f'font-size="{size}px" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}">{esc(text)}</text>'
    )


def rounded_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float = 12,
    fill: str = CARD,
    stroke: str = BORDER,
    stroke_width: float = 1,
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" ry="{radius}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def svg_doc(width: int, height: int, inner: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="18" fill="{BG}"/>
  {rounded_rect(1, 1, width - 2, height - 2, radius=18, fill=CARD, stroke=BORDER)}
  {inner}
</svg>
'''


def progress_bar(
    x: float,
    y: float,
    width: float,
    height: float,
    value: int,
    total: int,
    fill: str,
    background: str = "#292929",
) -> str:
    pct = percentage(value, total)
    filled_width = width * pct / 100
    return f'''
    <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{height / 2}" fill="{background}"/>
    <rect x="{x}" y="{y}" width="{filled_width:.2f}" height="{height}" rx="{height / 2}" fill="{fill}"/>
    '''


def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Generated {path.relative_to(ROOT)}")

# =========================================================
# Codolio data
# =========================================================


def fallback_codio() -> dict:
    return {
        "dsa": {
            "total": 326,
            "easy": 125,
            "medium": 145,
            "hard": 19,
            "other": 37,
        },
        "maxStreak": 24,
        "submissions": 656,
        "totalActiveDays": 181,
        "currentStreak": 4,
        "contest": {"rating": 1585, "contests": 14},
        "github": {"stars": 28, "pullRequests": 9, "issues": 5, "contributions": 849},
    }


def fetch_codio() -> dict:
    try:
        return get(CODIO_STATS_URL).json()
    except Exception as exc:
        print(f"Codolio refresh failed; using fallback data: {exc}")
        return fallback_codio()

# =========================================================
# Card 1 — About / Profile
# =========================================================


def fetch_avatar_data_uri() -> str:
    try:
        response = get(f"https://github.com/{USERNAME}.png?size=512")
        return "data:image/png;base64," + base64.b64encode(response.content).decode("ascii")
    except Exception as exc:
        print(f"Avatar fetch failed: {exc}")
        return ""


def generate_about() -> None:
    avatar = fetch_avatar_data_uri()
    image = ""
    fallback = ""

    if avatar:
        image = (
            f'<image href="{avatar}" x="24" y="24" width="220" height="220" '
            'preserveAspectRatio="xMidYMid slice" clip-path="url(#avatarClip)"/>'
        )
    else:
        fallback = '<text x="134" y="145" fill="#d1d5db" text-anchor="middle" font-size="54" font-weight="700">DK</text>'

    inner = f'''<defs>
      <clipPath id="avatarClip"><rect x="24" y="24" width="220" height="220" rx="14"/></clipPath>
    </defs>
    <rect x="24" y="24" width="220" height="220" rx="14" fill="#202020"/>
    {image}
    {fallback}

    {svg_text(f"{USERNAME} / README.md", 278, 56, size=11, fill="#707070", family="ui-monospace, SFMono-Regular, Menlo, monospace")}
    {svg_text("Howdy!", 278, 92, size=28, fill="#F5F5F5", weight=700)}
    {svg_text("I'm a developer focused on AI/ML, GenAI, data and backend systems.", 278, 122, size=13, fill="#C6C6C6")}
    {svg_text("I like turning ideas into practical tools and learning by building.", 278, 146, size=13, fill="#C6C6C6")}
    {svg_text("Currently exploring FastAPI, Django, Python, React/Next.js, and modern AI stacks.", 278, 170, size=13, fill="#C6C6C6")}
    {svg_text("My focus is strong fundamentals, useful projects, and clean engineering.", 278, 194, size=13, fill="#C6C6C6")}

    <line x1="278" y1="214" x2="838" y2="214" stroke="#2B2B2B"/>
    {svg_text("CURRENTLY BUILDING", 278, 242, size=11, fill="#989898", weight=700, family="ui-monospace, SFMono-Regular, Menlo, monospace")}
    {svg_text("AI/ML projects • backend systems • data-driven developer tooling", 278, 266, size=13, fill="#F0F0F0")}
    '''

    write_svg(OUTPUTS["about"], svg_doc(870, 290, inner))

# =========================================================
# Card 2 — Codolio DSA statistics (Compact Layout)
# =========================================================


def generate_dsa_stats(data: dict | None = None) -> None:
    """Generate assets/dsa-stats.svg using the existing Codolio JSON source with trimmed proportions."""
    data = data or fetch_codio()
    dsa = data.get("dsa", {})

    total = int(dsa.get("total", data.get("totalQuestions", 0)) or 0)
    easy = int(dsa.get("easy", 0) or 0)
    medium = int(dsa.get("medium", 0) or 0)
    hard = int(dsa.get("hard", 0) or 0)
    other = int(dsa.get("other", 0) or 0)

    submissions = int(data.get("submissions", 0) or 0)
    max_streak = int(data.get("maxStreak", 0) or 0)
    current_streak = int(data.get("currentStreak", 0) or 0)
    active_days = int(data.get("totalActiveDays", 0) or 0)

    contest = data.get("contest", {}) or {}
    contest_rating = int(contest.get("rating", 0) or 0)
    contests = int(contest.get("contests", 0) or 0)

    width, height = 400, 260
    parts: list[str] = []

    # Header
    parts.append(svg_text("DSA STATISTICS", 24, 32, size=12, fill=SECONDARY, weight=700))
    parts.append(svg_text("CODOLIO", width - 24, 32, size=11, fill=MUTED, weight=600, anchor="end"))

    # Solved block (left)
    parts.append(svg_text(format_number(total), 24, 76, size=38, fill=PRIMARY, weight=700))
    parts.append(svg_text("QUESTIONS SOLVED", 25, 96, size=9, fill=SECONDARY, weight=600))

    # Contest pill (left)
    parts.append('<rect x="24" y="112" width="128" height="42" rx="8" fill="#202020" stroke="#2D2D2D"/>')
    parts.append(svg_text(f"★ {format_number(contest_rating)}", 34, 131, size=14, fill=PRIMARY, weight=700))
    parts.append(svg_text(f"{contests} contests", 34, 145, size=9, fill=MUTED))
    parts.append(svg_text(f"{current_streak}d streak", 142, 131, size=11, fill=GREEN, weight=600, anchor="end"))

    # Difficulty bars (right)
    parts.append(svg_text("DIFFICULTY", 175, 54, size=10, fill=SECONDARY, weight=700))
    rows = [
        ("Easy", easy, GREEN),
        ("Medium", medium, MEDIUM),
        ("Hard", hard, HARD),
        ("Other", other, OTHER),
    ]

    for idx, (label, value, color) in enumerate(rows):
        y = 66 + idx * 24
        parts.append(svg_text(label, 175, y + 8, size=11, fill=PRIMARY, weight=500))
        parts.append(progress_bar(222, y, 108, 6, value, total, color))
        parts.append(svg_text(format_number(value), width - 24, y + 8, size=11, fill=PRIMARY, weight=600, anchor="end"))

    # Divider
    parts.append(f'<line x1="24" y1="172" x2="{width - 24}" y2="172" stroke="{BORDER}" stroke-width="1"/>')

    # Bottom 4 quick stats
    stats = [
        ("MAX STREAK", f"{max_streak}d", 24),
        ("SUBMISSIONS", format_number(submissions), 120),
        ("ACTIVE DAYS", f"{active_days}d", 220),
        ("CONTESTS", format_number(contests), 320),
    ]

    for label, value, x in stats:
        parts.append(svg_text(value, x, 206, size=18, fill=PRIMARY, weight=700))
        parts.append(svg_text(label, x, 224, size=9, fill=SECONDARY, weight=600))

    write_svg(OUTPUTS["dsa"], svg_doc(width, height, "\n".join(parts)))

# =========================================================
# Card 3 — GitHub contribution graph
# =========================================================


def parse_contributions(days_html: str) -> tuple[dict[dt.date, tuple[int, int]], int]:
    # 1. Parse total count from H2 if available
    total_m = re.search(r'([0-9,]+)\s+contributions\s+in the last year', days_html)
    total_count = int(total_m.group(1).replace(",", "")) if total_m else 0

    # 2. Extract daily cells (handles any order of attributes in <td>)
    cells_raw = re.findall(r'<td[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d+)"', days_html)
    if not cells_raw:
        cells_raw = [(d, l) for l, d in re.findall(r'<td[^>]*?data-level="(\d+)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"', days_html)]

    # 3. Tooltips to get exact count per day
    tooltips = dict(re.findall(r'<tool-tip[^>]*?for="([^"]+)"[^>]*>(.*?)</tool-tip>', days_html, re.DOTALL))
    id_date_map = dict(re.findall(r'<td[^>]*?id="([^"]+)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"', days_html))
    date_id_map = {d: i for i, d in id_date_map.items()}

    out: dict[dt.date, tuple[int, int]] = {}
    computed_total = 0

    for date_s, level_s in cells_raw:
        day = dt.date.fromisoformat(date_s)
        level = int(level_s)
        count = 0
        tip_id = date_id_map.get(date_s)
        if tip_id and tip_id in tooltips:
            m = re.search(r'(\d+)\s+contribution', tooltips[tip_id])
            if m:
                count = int(m.group(1))
        elif level > 0:
            count = level

        out[day] = (level, count)
        computed_total += count

    final_total = total_count if total_count > 0 else computed_total
    return out, final_total


def fetch_contributions() -> tuple[dict[dt.date, tuple[int, int]], int]:
    today = dt.date.today()
    start = today - dt.timedelta(days=365)
    params = urlencode({"from": start.isoformat(), "to": today.isoformat()})
    url = f"https://github.com/users/{USERNAME}/contributions?{params}"

    response = get(url, headers={"Accept": "text/html"})
    cells, total = parse_contributions(response.text)
    if not cells:
        raise RuntimeError("Could not parse GitHub contribution calendar")
    return cells, total


def month_positions(start: dt.date, end: dt.date, x0: int, col_w: int) -> list[tuple[str, int]]:
    positions: list[tuple[str, int]] = []
    current = dt.date(start.year, start.month, 1)

    while current <= end:
        sunday = current - dt.timedelta(days=(current.weekday() + 1) % 7)
        col = (sunday - start).days // 7
        if 0 <= col <= 60:
            positions.append((current.strftime("%b"), x0 + col * col_w))

        if current.month == 12:
            current = dt.date(current.year + 1, 1, 1)
        else:
            current = dt.date(current.year, current.month + 1, 1)

    return positions


def generate_contributions() -> None:
    try:
        cells, total = fetch_contributions()
    except Exception as exc:
        previous = OUTPUTS["contributions"]
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

    inner: list[str] = [
        svg_text(f"{total:,} contributions in the last year", 34, 48, size=23, fill=PRIMARY, weight=700),
        '<rect x="752" y="28" width="82" height="34" rx="8" fill="#202020" stroke="#2D2D2D"/>',
        svg_text(dt.date.today().year, 767, 50, size=12, fill="#C6C6C6"),
        svg_text("⌄", 821, 50, size=10, fill="#6F6F6F", anchor="end"),
    ]

    for label, x in month_positions(start, end, x0, col_w):
        inner.append(svg_text(label, x, 76, size=10, fill="#777777"))

    for day, (level, count) in cells.items():
        col = (day - start).days // 7
        row = (day.weekday() + 1) % 7
        color = CONTRIBUTION_COLORS[min(max(level, 0), 4)]
        x = x0 + col * col_w
        y = y0 + row * col_w
        title = esc(f"{day.isoformat()}: {count} contributions")
        inner.append(
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2.5" fill="{color}"><title>{title}</title></rect>'
        )

    # Legend
    lx = 664
    inner.append(svg_text("Less", lx - 58, 204, size=10, fill="#767676"))
    for i, color in enumerate(CONTRIBUTION_COLORS):
        inner.append(f'<rect x="{lx + i * 14}" y="195" width="10" height="10" rx="2" fill="{color}"/>')
    inner.append(svg_text("More", lx + 5 * 14 + 4, 204, size=10, fill="#767676"))

    write_svg(OUTPUTS["contributions"], svg_doc(870, 235, "\n".join(inner)))

# =========================================================
# Card 4 — Popular & Pinned repositories
# =========================================================


def fetch_pinned_names() -> list[str]:
    """Scrape pinned repository names from user's GitHub profile."""
    try:
        response = get(f"https://github.com/{USERNAME}", headers={"Accept": "text/html"})
        pinned = re.findall(r'<span class="repo"[^>]*>([^<]+)</span>', response.text)
        return [name.strip() for name in pinned if name.strip()]
    except Exception as exc:
        print(f"Could not fetch pinned repos from profile: {exc}")
        return []


def fetch_repos() -> list[dict]:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = get(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated",
        headers=headers,
    )

    repos = response.json()
    if not isinstance(repos, list):
        return []

    repo_map = {
        r.get("name", "").lower(): r
        for r in repos
        if isinstance(r, dict)
        and not r.get("fork")
        and not r.get("archived")
        and r.get("name") != USERNAME
    }

    # 1. Try to match pinned repositories first
    pinned_names = fetch_pinned_names()
    matched_pinned = []
    for name in pinned_names:
        lower = name.lower()
        if lower in repo_map:
            matched_pinned.append(repo_map[lower])

    if matched_pinned:
        return matched_pinned[:4]

    # 2. Fallback to top repositories sorted by stars/updated
    remaining = list(repo_map.values())
    remaining.sort(
        key=lambda repo: (
            repo.get("stargazers_count", 0),
            repo.get("forks_count", 0),
            repo.get("updated_at", ""),
        ),
        reverse=True,
    )
    return remaining[:4]


def compact(text_value: str, width: int = 40) -> str:
    value = (text_value or "No description provided.").replace("\n", " ").strip()
    return textwrap.shorten(value, width=width, placeholder="…")


def generate_popular_repos() -> None:
    try:
        repos = fetch_repos()
    except Exception as exc:
        print(f"Repository refresh failed: {exc}")
        repos = []

    inner = [
        svg_text("Popular repositories", 28, 42, size=21, fill=PRIMARY, weight=700),
        svg_text("⌄", 205, 42, size=11, fill="#777"),
    ]

    positions = [(28, 58), (312, 58), (28, 200), (312, 200)]

    for index, (x, y) in enumerate(positions):
        repo = repos[index] if index < len(repos) else None
        inner.append(f'<rect x="{x}" y="{y}" width="260" height="124" rx="12" fill="{CARD_2}" stroke="#2C2C2C"/>')

        if not repo:
            inner.append(svg_text("Repository data unavailable", x + 18, y + 28, size=13, fill="#666666"))
            continue

        name = esc(repo.get("name", "unknown"))
        language = esc(repo.get("language") or "—")
        desc = esc(compact(repo.get("description") or "", 42))
        stars = format_number(repo.get("stargazers_count", 0))
        forks = format_number(repo.get("forks_count", 0))

        inner.extend(
            [
                svg_text(f"▱  {name}", x + 18, y + 28, size=14, fill="#F2F2F2", weight=600, family="ui-monospace, SFMono-Regular, Menlo, monospace"),
                svg_text(desc, x + 18, y + 50, size=12, fill="#9A9A9A"),
                svg_text(f"★ {stars}   ⑂ {forks}", x + 18, y + 74, size=11, fill="#A7A7A7"),
                svg_text(language, x + 18, y + 100, size=10, fill="#6F6F6F"),
            ]
        )

    write_svg(OUTPUTS["repos"], svg_doc(590, 350, "\n".join(inner)))

# =========================================================
# Card 5 — Official GitHub Achievements
# =========================================================

ACHIEVEMENT_META = {
    "pull shark": {
        "title": "Pull Shark",
        "desc": "Merged pull requests",
        "fallback_url": "https://github.githubassets.com/assets/pull-shark-default-498c279a747d.png",
    },
    "pair extraordinaire": {
        "title": "Pair Extraordinaire",
        "desc": "Co-authored commits",
        "fallback_url": "https://github.githubassets.com/assets/pair-extraordinaire-default-579438a20e01.png",
    },
    "quickdraw": {
        "title": "Quickdraw",
        "desc": "Closed issue or PR in <5m",
        "fallback_url": "https://github.githubassets.com/assets/quickdraw-default-39c6aec8ff89.png",
    },
    "yolo": {
        "title": "YOLO",
        "desc": "Merged PR without review",
        "fallback_url": "https://github.githubassets.com/assets/yolo-default-be0bbff42e13.png",
    },
    "galaxy brain": {
        "title": "Galaxy Brain",
        "desc": "Accepted discussion answers",
        "fallback_url": "https://github.githubassets.com/assets/galaxy-brain-default-35a47d9ca46b.png",
    },
    "starstruck": {
        "title": "Starstruck",
        "desc": "Created 16★ repository",
        "fallback_url": "https://github.githubassets.com/assets/starstruck-default-b6610abad518.png",
    },
}


def fetch_badge_data_uri(url: str) -> str:
    """Download badge image and convert to base64 Data URI."""
    try:
        res = get(url, timeout=10)
        return "data:image/png;base64," + base64.b64encode(res.content).decode("ascii")
    except Exception as exc:
        print(f"Could not load badge image from {url}: {exc}")
        return ""


def fetch_github_achievements() -> list[dict]:
    """Scrape unlocked GitHub achievements from user profile."""
    try:
        res = get(f"https://github.com/{USERNAME}", headers={"Accept": "text/html"})
        matches = re.findall(
            r'src="([^"]+)"[^>]*?alt="Achievement:\s*([^"]+)"',
            res.text,
        )
        if not matches:
            # Try alternate attribute ordering
            matches = [
                (src, alt)
                for alt, src in re.findall(
                    r'alt="Achievement:\s*([^"]+)"[^>]*?src="([^"]+)"',
                    res.text,
                )
            ]

        seen = set()
        achievements = []
        for src, name in matches:
            clean_name = name.strip()
            lower = clean_name.lower()
            if lower not in seen:
                seen.add(lower)
                meta = ACHIEVEMENT_META.get(
                    lower,
                    {"title": clean_name, "desc": "GitHub Achievement", "fallback_url": src},
                )
                achievements.append({
                    "name": meta["title"],
                    "desc": meta["desc"],
                    "image_url": src or meta.get("fallback_url", ""),
                })

        if achievements:
            return achievements
    except Exception as exc:
        print(f"Failed to scrape GitHub achievements: {exc}")

    # Fallback to default earned badges
    return [
        {
            "name": ACHIEVEMENT_META["pull shark"]["title"],
            "desc": ACHIEVEMENT_META["pull shark"]["desc"],
            "image_url": ACHIEVEMENT_META["pull shark"]["fallback_url"],
        },
        {
            "name": ACHIEVEMENT_META["pair extraordinaire"]["title"],
            "desc": ACHIEVEMENT_META["pair extraordinaire"]["desc"],
            "image_url": ACHIEVEMENT_META["pair extraordinaire"]["fallback_url"],
        },
    ]


def generate_achievements(data: dict | None = None) -> None:
    width, height = 320, 350
    achievements = fetch_github_achievements()

    inner = [
        svg_text("GitHub Achievements", 24, 38, size=18, fill=PRIMARY, weight=700),
        svg_text("official profile badges", 24, 56, size=10, fill="#707070"),
    ]

    y_start = 72
    card_h = 105
    card_w = 272

    # Render up to 2 large earned badge cards
    for idx, ach in enumerate(achievements[:2]):
        y = y_start + idx * (card_h + 12)
        inner.append(f'<rect x="24" y="{y}" width="{card_w}" height="{card_h}" rx="12" fill="{CARD_2}" stroke="#2C2C2C"/>')

        # Badge artwork
        b64 = fetch_badge_data_uri(ach["image_url"])
        if b64:
            inner.append(
                f'<image href="{b64}" x="34" y="{y + 20}" width="64" height="64" preserveAspectRatio="xMidYMid meet"/>'
            )

        inner.extend([
            svg_text(ach["name"], 108, y + 36, size=14, fill=PRIMARY, weight=700),
            svg_text(ach["desc"], 108, y + 56, size=11, fill="#9A9A9A"),
            f'<rect x="108" y="{y + 68}" width="78" height="20" rx="6" fill="#143e22" stroke="#26a641" stroke-width="0.8"/>',
            svg_text("✦ Unlocked", 147, y + 82, size=9, fill="#39D353", weight=700, anchor="middle"),
        ])

    inner.append(f'<line x1="24" y1="{height - 36}" x2="{width - 24}" y2="{height - 36}" stroke="#2B2B2B"/>')
    inner.append(svg_text("data source: GitHub Profile Achievements", 24, height - 16, size=9, fill="#686868"))

    write_svg(OUTPUTS["achievements"], svg_doc(width, height, "\n".join(inner)))

# =========================================================
# Main
# =========================================================


def main() -> None:
    print(f"Refreshing GitHub profile cards for @{USERNAME}...")

    codio = fetch_codio()

    # About card
    generate_about()

    # IMPORTANT: keep this optional so the existing dedicated DSA workflow
    # can remain the owner of assets/dsa-stats.svg.
    if GENERATE_DSA:
        generate_dsa_stats(codio)
    else:
        print("Skipping Codolio DSA card (GENERATE_DSA=false).")

    # Remaining dashboard cards
    generate_contributions()
    generate_popular_repos()
    generate_achievements(codio)

    print("Profile dashboard cards refreshed successfully.")


if __name__ == "__main__":
    main()

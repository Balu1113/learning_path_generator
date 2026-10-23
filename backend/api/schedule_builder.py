"""Turn a saved learning path into dated daily study blocks."""
import json
import re
from datetime import date, timedelta

from chains.path_generator import parse_markdown_phases

_BULLET_RE = re.compile(r"^\s{0,3}[-*+•]\s+(.*\S)\s*$")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_STYLE_RE = re.compile(r"[*_`#>]")


def _clean(text):
    text = _MD_LINK_RE.sub(r"\1", text or "")
    text = _MD_STYLE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def structured_phases(path):
    try:
        return json.loads(path["content"]).get("phases", [])
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def markdown_topics(body):
    topics = []
    for line in (body or "").splitlines():
        m = _BULLET_RE.match(line)
        if m:
            title = _clean(m.group(1))
            if title:
                topics.append({"title": title[:160], "details": "", "resources": []})
    return topics


def path_phases(path):
    """Normalize both path formats to [{title, estimated_weeks, topics}]."""
    if path["metadata"].get("format") == "structured":
        out = []
        for phase in structured_phases(path):
            out.append({
                "title": phase.get("title", "Phase"),
                "estimated_weeks": _as_int(phase.get("estimated_weeks"), 4),
                "topics": [
                    {
                        "title": t.get("title", ""),
                        "details": t.get("details", ""),
                        "resources": t.get("resources", []) or [],
                    }
                    for t in (phase.get("topics") or [])
                    if t.get("title")
                ],
            })
        return out

    phases = []
    for phase in parse_markdown_phases(path["content"]):
        topics = markdown_topics(phase.get("raw", ""))
        phases.append({
            "title": phase.get("title", "Phase"),
            "estimated_weeks": max(1, round(len(topics) / 5)) if topics else 1,
            "topics": topics,
        })
    return phases


def _as_int(value, default):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def study_dates(start, days_per_week, count):
    """Calendar days from `start`, studying on the first `days_per_week` weekdays."""
    if count <= 0:
        return []
    dpw = max(1, min(7, int(days_per_week or 5)))
    out = []
    cursor = start
    while len(out) < count:
        if cursor.weekday() < dpw:
            out.append(cursor)
        cursor += timedelta(days=1)
    return out


def _calendar_weeks(day_map, start, last_date):
    """Mon-aligned 7-day windows covering every study day.

    Each window carries all seven calendar days so a calendar grid can render
    non-study days as empty slots instead of silently dropping them.
    """
    if not last_date:
        return []
    cursor = start - timedelta(days=start.weekday())
    last = date.fromisoformat(last_date)
    weeks = []
    while cursor <= last:
        days = []
        for offset in range(7):
            day = cursor + timedelta(days=offset)
            iso = day.isoformat()
            entry = day_map.get(iso)
            days.append({
                "date": iso,
                "weekday": day.weekday(),
                "study": entry is not None,
                "hours": round(sum(b["hours"] for b in entry), 2) if entry else 0,
                "blocks": entry or [],
            })
        weeks.append({
            "index": len(weeks) + 1,
            "start": cursor.isoformat(),
            "end": (cursor + timedelta(days=6)).isoformat(),
            "hours": round(sum(d["hours"] for d in days), 2),
            "blocks": sum(len(d["blocks"]) for d in days),
            "days": days,
        })
        cursor += timedelta(days=7)
    return weeks


def _phase_plan(phases, blocks):
    """Per-phase summary: how many topics, how much time, and which dates."""
    plan = []
    for phase in phases:
        title = phase["title"]
        owned = [b for b in blocks if b["phase_title"] == title]
        if not owned:
            continue
        plan.append({
            "title": title,
            "topics": len(phase["topics"]),
            "blocks": len(owned),
            "hours": round(sum(b["hours"] for b in owned), 2),
            "start": owned[0]["date"],
            "end": owned[-1]["date"],
        })
    return plan


def build_schedule(path, start=None, days_per_week=5, hours_per_day=None):
    meta = path["metadata"]
    start = start or date.today()
    dpw = max(1, min(7, int(days_per_week or 5)))
    try:
        hours = float(hours_per_day or meta.get("hours_per_day") or 2)
    except (TypeError, ValueError):
        hours = 2.0
    hours = max(0.5, hours)

    phases = path_phases(path)
    blocks = []

    if phases:
        phase_windows = []
        for phase in phases:
            n = len(phase["topics"])
            window = max(n, phase["estimated_weeks"] * dpw) if n else phase["estimated_weeks"] * dpw
            phase_windows.append(max(1, window))

        total_days = sum(phase_windows)
        all_days = study_dates(start, dpw, total_days)

        cursor = 0
        for phase, window in zip(phases, phase_windows):
            days = all_days[cursor:cursor + window]
            cursor += window
            topics = phase["topics"]
            if not topics or not days:
                continue
            step = max(1, len(days) // len(topics))
            for i, topic in enumerate(topics):
                day_index = min(i * step, len(days) - 1)
                blocks.append({
                    "date": days[day_index].isoformat(),
                    "phase_title": phase["title"],
                    "title": topic["title"],
                    "details": topic.get("details", ""),
                    "resources": topic.get("resources", []),
                    "hours": hours,
                })
    else:
        all_days = study_dates(start, dpw, 1)

    blocks.sort(key=lambda b: b["date"])
    for i, block in enumerate(blocks):
        block["id"] = f"b{i}"

    day_map = {}
    for block in blocks:
        day_map.setdefault(block["date"], []).append(block)

    days = [
        {
            "date": d,
            "study": d in day_map,
            "blocks": day_map.get(d, []),
            "hours": round(sum(b["hours"] for b in day_map.get(d, [])), 2),
        }
        for d in sorted(day_map)
    ]

    last_date = days[-1]["date"] if days else None

    return {
        "start": start.isoformat(),
        "days_per_week": dpw,
        "hours_per_day": hours,
        "total_blocks": len(blocks),
        "total_hours": round(sum(b["hours"] for b in blocks), 2),
        "end_date": last_date,
        "days": days,
        "weeks": _calendar_weeks(day_map, start, last_date),
        "phases": [p["title"] for p in phases],
        "phase_plan": _phase_plan(phases, blocks),
    }

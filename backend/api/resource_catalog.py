"""Curated resource catalog: upserts, URL health checks, search, and generation hooks."""
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from django.db.models import Q

from .models import Resource

STALE_AFTER_DAYS = 90
HEALTH_TIMEOUT_SECONDS = 6
USER_AGENT = "LearnPathBot/1.0 (+resource-verification)"
VALID_TYPES = {"course", "book", "video", "article", "tool", "docs", "interactive"}
VALID_LEVELS = {"beginner", "intermediate", "advanced", "all"}
VALID_COSTS = {"free", "freemium", "paid"}


def _now():
    return datetime.now(tz=timezone.utc)


def normalize_name(name: str) -> str:
    return " ".join((name or "").lower().split())


def check_url_health(url: str) -> dict:
    """Check a URL with HEAD (falling back to GET). Never raises."""

    def _attempt(method):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT_SECONDS) as resp:
            return resp.status, resp.geturl()

    try:
        try:
            status, final = _attempt("HEAD")
        except urllib.error.HTTPError as e:
            if e.code in (403, 405, 501):
                status, final = _attempt("GET")
            else:
                return {"health": "broken", "final_url": url, "status_code": e.code}
        except urllib.error.URLError:
            return {"health": "broken", "final_url": url, "status_code": None}
    except Exception:
        return {"health": "broken", "final_url": url, "status_code": None}

    if 200 <= status < 300:
        health = "redirect" if final and final.rstrip("/") != url.rstrip("/") else "ok"
        return {"health": health, "final_url": final or url, "status_code": status}
    if status in (401, 403):
        # Paywalls/auth walls still mean the resource exists.
        return {"health": "ok", "final_url": final or url, "status_code": status}
    return {"health": "broken", "final_url": final or url, "status_code": status}


def is_stale(resource: Resource, now=None) -> bool:
    now = now or _now()
    if resource.url_health == "broken":
        return True
    if resource.verified_at is None:
        return True
    verified = resource.verified_at
    if verified.tzinfo is None:
        verified = verified.replace(tzinfo=timezone.utc)
    return (now - verified) > timedelta(days=STALE_AFTER_DAYS)


def upsert_resource(
    url: str,
    name: str,
    type: str = "article",
    level: str = "beginner",
    cost: str = "free",
    duration_hours=None,
    domain: str = "",
    description: str = "",
    content_source: str = "ai_generated",
    check_health: bool = True,
) -> Resource:
    url = (url or "").strip()
    name = (name or "").strip()
    if not url or not name:
        raise ValueError("url and name are required")
    type = type if type in VALID_TYPES else "article"
    level = level if level in VALID_LEVELS else "beginner"
    cost = cost if cost in VALID_COSTS else "free"
    try:
        duration = float(duration_hours) if duration_hours is not None else None
    except (TypeError, ValueError):
        duration = None

    row = Resource.objects.filter(url=url).first()
    created = row is None
    if row is None:
        row = Resource(url=url, name=name, content_source=content_source)
    updates = {
        "name": name,
        "type": type,
        "level": level,
        "cost": cost,
        "duration_hours": duration,
        "domain": (domain or "").strip()[:80],
        "description": (description or "").strip(),
    }
    for key, value in updates.items():
        setattr(row, key, value)
    # Admin-curated status is never downgraded by re-ingest.
    if created:
        row.content_source = content_source
    if check_health:
        result = check_url_health(url)
        row.url_health = result["health"]
        row.final_url = result.get("final_url", "")[:500]
        row.verified_at = _now()
    row.save()
    return row


def verify_resource(resource: Resource) -> Resource:
    result = check_url_health(resource.url)
    resource.url_health = result["health"]
    resource.final_url = result.get("final_url", "")[:500]
    resource.verified_at = _now()
    resource.save(update_fields=["url_health", "final_url", "verified_at", "updated_at"])
    return resource


def serialize_resource(r: Resource, now=None) -> dict:
    return {
        "id": r.id,
        "url": r.url,
        "name": r.name,
        "type": r.type,
        "level": r.level,
        "cost": r.cost,
        "duration_hours": r.duration_hours,
        "domain": r.domain,
        "description": r.description,
        "content_source": r.content_source,
        "url_health": r.url_health,
        "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        "community_rating": r.community_rating,
        "rating_count": r.rating_count,
        "stale": is_stale(r, now),
        "trusted": r.content_source == "curated" and r.url_health in ("ok", "redirect") and not is_stale(r, now),
    }


def search_catalog(query: str = "", domain: str = "", difficulty: str = "", limit: int = 12) -> list[Resource]:
    qs = Resource.objects.all()
    query = (query or "").strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(domain__icontains=query.replace(" ", "_"))
        )
    domain = (domain or "").strip()
    if domain:
        qs = qs.filter(domain=domain)
    difficulty = (difficulty or "").strip().lower()
    if difficulty and difficulty != "any":
        qs = qs.filter(level=difficulty)
    # Prefer healthy, verified entries; broken links sink to the bottom.
    qs = qs.extra(
        select={"broken": "url_health = 'broken'"},
        order_by=["broken", "-verified_at", "-community_rating", "name"],
    )
    return list(qs[: max(1, min(50, limit))])


def search_result_item(r: Resource) -> dict:
    """Catalog row shaped like the legacy search result, plus quality fields."""
    s = serialize_resource(r)
    return {
        "metadata": {
            "topic_name": r.name,
            "domain": r.domain or "general",
            "category": r.type,
            "difficulty": r.level,
            "estimated_hours": r.duration_hours or 0,
            "description": r.description,
            "url": r.url,
            "cost": r.cost,
            "rating": r.community_rating,
            "rating_count": r.rating_count,
            "verified": r.url_health in ("ok", "redirect") and not s["stale"],
            "stale": s["stale"],
            "broken": r.url_health == "broken",
            "content_source": r.content_source,
            "source": "catalog",
        },
    }


def catalog_for_generation(goal: str, limit: int = 12) -> list[Resource]:
    terms = [t for t in (goal or "").replace(",", " ").split() if len(t) > 2]
    rows: list[Resource] = []
    seen = set()
    for term in terms[:4]:
        for r in search_catalog(query=term, limit=limit):
            if r.id not in seen and r.url_health in ("ok", "redirect", "unknown") and not is_stale(r):
                seen.add(r.id)
                rows.append(r)
        if len(rows) >= limit:
            break
    if not rows:
        rows = search_catalog(query="", limit=limit)
    return rows[:limit]


def format_catalog_for_prompt(rows: list[Resource]) -> str:
    if not rows:
        return "none available yet"
    lines = []
    for r in rows:
        parts = [f"- {r.name} ({r.type}, {r.level}"]
        if r.cost and r.cost != "free":
            parts[0] += f", {r.cost}"
        if r.duration_hours:
            parts[0] += f", ~{r.duration_hours:g}h"
        parts[0] += ")"
        lines.append(parts[0])
        if r.description:
            lines.append(f"  {r.description[:160]}")
    return "\n".join(lines)


def catalog_index(rows: list[Resource]) -> dict:
    """Normalized name -> serialized catalog entry, for post-generation annotation."""
    return {normalize_name(r.name): serialize_resource(r) for r in rows}


def annotate_verified_resources(structured: dict, index: dict) -> dict:
    """Stamp catalog quality fields onto resources the LLM marked verified.

    A resource flagged verified but not found in the catalog is demoted to an
    AI suggestion so the UI never shows a false 'verified' badge.
    """
    if not isinstance(structured, dict):
        return structured
    for phase in structured.get("phases") or []:
        if not isinstance(phase, dict):
            continue
        for topic in phase.get("topics") or []:
            if not isinstance(topic, dict):
                continue
            for res in topic.get("resources") or []:
                if not isinstance(res, dict):
                    continue
                if res.pop("verified", False):
                    match = index.get(normalize_name(str(res.get("name", ""))))
                    if match:
                        res["url"] = match["url"]
                        res["cost"] = match["cost"]
                        res["level"] = match["level"]
                        res["rating"] = match["community_rating"]
                        res["source"] = "catalog"
                        res["verified"] = True
                    else:
                        res["source"] = "ai"
                        res["verified"] = False
                else:
                    res.setdefault("source", "ai")
                    res.setdefault("verified", False)
    return structured

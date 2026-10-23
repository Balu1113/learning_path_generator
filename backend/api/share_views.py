"""Public share links: unlisted /p/<slug> pages that show a roadmap read-only,
plus the public gallery that lists everything currently shared."""
import json
import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from chains.path_generator import parse_markdown_phases
from memory.vector_store import vector_memory
from .models import ShareLink
from .study_views import _load_path, _require_user

GALLERY_LIMIT = 100


def _new_slug():
    for _ in range(10):
        slug = secrets.token_urlsafe(9)
        if not ShareLink.objects.filter(slug=slug).exists():
            return slug
    raise RuntimeError("Could not allocate a unique share slug")


def _payload(link):
    return {"slug": link.slug, "url": f"/p/{link.slug}"}


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
def manage_share(request, doc_id):
    """Owner-managed share link for one saved path: create, inspect, or revoke."""
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err

    link = ShareLink.objects.filter(user=request.user, path_id=doc_id).first()

    if request.method == "GET":
        return JsonResponse({**_payload(link), "created": link is not None} if link
                            else {"slug": None, "url": None, "created": False})

    if request.method == "DELETE":
        if link:
            link.delete()
            return JsonResponse({"revoked": True})
        return JsonResponse({"revoked": False})

    if link:
        return JsonResponse({**_payload(link), "created": False})
    link = ShareLink.objects.create(user=request.user, path_id=doc_id, slug=_new_slug())
    return JsonResponse({**_payload(link), "created": True})


@require_GET
def shared_path(request, slug):
    """Public, read-only payload for a shared roadmap. No login required."""
    link = ShareLink.objects.filter(slug=slug).first()
    path = vector_memory.get_path(link.path_id) if link else None
    if path is None:
        return JsonResponse(
            {"error": "This share link is invalid or has been revoked."},
            status=404,
        )
    meta = dict(path["metadata"])
    meta.pop("owner", None)
    return JsonResponse({
        "id": path["id"],
        "goal": meta.get("goal", ""),
        "format": meta.get("format", "markdown"),
        "content": path["content"],
        "created_at": meta.get("created_at", ""),
        "metadata": meta,
    })


def _stats(path):
    meta = path["metadata"]
    fmt = meta.get("format", "markdown")
    title = summary = ""
    phase_count = 0
    topic_count = 0
    if fmt == "structured":
        try:
            s = json.loads(path["content"])
        except (json.JSONDecodeError, ValueError, TypeError):
            s = {}
        if isinstance(s, dict):
            title = str(s.get("title") or "").strip()
            summary = str(s.get("summary") or "").strip()
            phases = [ph for ph in (s.get("phases") or []) if isinstance(ph, dict)]
            phase_count = len(phases)
            topic_count = sum(len(ph.get("topics") or []) for ph in phases)
    else:
        md_phases = parse_markdown_phases(path["content"])
        phase_count = len(md_phases)
        topic_count = sum(
            1
            for ph in md_phases
            for line in (ph.get("raw") or "").splitlines()
            if line.strip().startswith(("-", "*"))
        )
    return {
        "title": title,
        "summary": summary[:200],
        "phase_count": phase_count,
        "topic_count": topic_count,
    }


@require_GET
def gallery(request):
    """Public list of currently shared roadmaps, newest share first."""
    items = []
    for link in ShareLink.objects.order_by("-created_at")[:GALLERY_LIMIT]:
        path = vector_memory.get_path(link.path_id)
        if path is None:
            continue
        meta = path["metadata"]
        items.append({
            "slug": link.slug,
            "goal": meta.get("goal", ""),
            "format": meta.get("format", "markdown"),
            "created_at": meta.get("created_at", ""),
            "shared_at": link.created_at.isoformat(),
            "hours_per_day": str(meta.get("hours_per_day", "") or ""),
            "months": str(meta.get("months", "") or ""),
            **_stats(path),
        })
    return JsonResponse({"items": items})

"""Resource catalog management: LLM ingest of candidate resources + URL verification."""
import json

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from chains.path_generator import generate_resource_ingest
from .resource_catalog import (
    search_catalog,
    search_result_item,
    serialize_resource,
    upsert_resource,
    verify_resource,
)
from .models import Resource
from .views import _json_body


def _admin_required(request):
    user = request.user
    if not (user.is_authenticated and user.is_superuser):
        return JsonResponse({"error": "Admin access required"}, status=403)
    return None


@csrf_exempt
@require_POST
def resources_ingest(request):
    """Ask the LLM for real resources on a topic, health-check them, and upsert
    them into the catalog as AI-generated candidates for admin review."""
    denied = _admin_required(request)
    if denied:
        return denied
    data = _json_body(request)
    query = (data.get("query") or "").strip()
    if not query:
        return JsonResponse({"error": "query is required"}, status=400)
    domain = (data.get("domain") or "").strip()
    difficulty = (data.get("difficulty") or "any").strip()
    try:
        count = int(data.get("count", 8))
    except (TypeError, ValueError):
        count = 8

    try:
        result = generate_resource_ingest(query, domain=domain, difficulty=difficulty, count=count)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    items = result.get("resources") or []
    if not isinstance(items, list) or not items:
        return JsonResponse({"error": "The model returned no resources."}, status=502)

    created = 0
    updated = 0
    skipped = 0
    rows = []
    for it in items:
        if not isinstance(it, dict):
            skipped += 1
            continue
        url = str(it.get("url") or "").strip()
        name = str(it.get("name") or "").strip()
        if not url.startswith(("http://", "https://")) or not name:
            skipped += 1
            continue
        existed = Resource.objects.filter(url=url).exists()
        try:
            row = upsert_resource(
                url=url,
                name=name,
                type=str(it.get("type") or "article"),
                level=str(it.get("level") or "beginner"),
                cost=str(it.get("cost") or "free"),
                duration_hours=it.get("duration_hours"),
                domain=str(it.get("domain") or domain),
                description=str(it.get("description") or ""),
                content_source="ai_generated",
            )
        except ValueError:
            skipped += 1
            continue
        rows.append(serialize_resource(row))
        if existed:
            updated += 1
        else:
            created += 1

    return JsonResponse({
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "resources": rows,
    })


@require_GET
def resources_catalog(request):
    """Search the catalog directly (quality metadata included)."""
    query = request.GET.get("query", "").strip()
    domain = request.GET.get("domain", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()
    try:
        limit = int(request.GET.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    rows = search_catalog(query=query, domain=domain, difficulty=difficulty, limit=limit)
    return JsonResponse({
        "results": [serialize_resource(r) for r in rows],
        "count": len(rows),
    })


@csrf_exempt
@require_POST
def resources_verify(request, resource_id):
    """Re-check a catalog entry's URL health."""
    denied = _admin_required(request)
    if denied:
        return denied
    row = Resource.objects.filter(id=resource_id).first()
    if row is None:
        return JsonResponse({"error": "Resource not found"}, status=404)
    verify_resource(row)
    return JsonResponse({"resource": serialize_resource(row)})


@csrf_exempt
@require_POST
def resources_promote(request, resource_id):
    """Admin: mark an AI-generated candidate as curated (or revert)."""
    denied = _admin_required(request)
    if denied:
        return denied
    row = Resource.objects.filter(id=resource_id).first()
    if row is None:
        return JsonResponse({"error": "Resource not found"}, status=404)
    data = _json_body(request)
    source = (data.get("content_source") or "curated").strip()
    if source not in ("curated", "ai_generated"):
        return JsonResponse({"error": "content_source must be curated or ai_generated"}, status=400)
    row.content_source = source
    row.save(update_fields=["content_source", "updated_at"])
    return JsonResponse({"resource": serialize_resource(row)})

import json
from datetime import date, datetime
from functools import wraps

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET

from memory.vector_store import vector_memory
from .models import Badge, Feedback, Flashcard, MilestoneProject, PathProgress, Resource, Skill, StudyActivity, TestResult

User = get_user_model()

RESOURCES = {
    "users": {
        "model": User,
        "label": "Users",
        "fields": ["username", "password", "email", "first_name", "last_name",
                   "is_active", "is_staff", "is_superuser"],
        "display": ["username", "email", "is_active", "is_staff", "is_superuser",
                    "date_joined", "last_login"],
        "search": ["username", "email"],
        "write_only": ["password"],
        "special": "user",
    },
    "feedback": {
        "model": Feedback,
        "label": "Feedback",
        "fields": ["path_id", "user", "value"],
        "display": ["path_id", "user", "value", "created_at"],
        "search": ["path_id"],
        "fk": ["user"],
    },
    "progress": {
        "model": PathProgress,
        "label": "Path progress",
        "fields": ["user", "path_id", "item_key", "done"],
        "display": ["user", "path_id", "item_key", "done", "updated_at"],
        "search": ["path_id", "item_key"],
        "fk": ["user"],
    },
    "flashcards": {
        "model": Flashcard,
        "label": "Flashcards",
        "fields": ["user", "path_id", "front", "back", "topic", "phase_idx", "ease",
                   "interval_days", "reps", "lapses", "due_at", "last_review_at"],
        "display": ["user", "path_id", "front", "topic", "reps", "lapses", "ease",
                    "interval_days", "due_at", "created_at"],
        "search": ["path_id", "front", "back", "topic"],
        "fk": ["user"],
    },
    "activity": {
        "model": StudyActivity,
        "label": "Study activity",
        "fields": ["user", "date", "kind", "count"],
        "display": ["user", "date", "kind", "count"],
        "search": ["kind"],
        "fk": ["user"],
    },
    "tests": {
        "model": TestResult,
        "label": "Test results",
        "fields": ["user", "path_id", "phase_idx", "phase_title", "score", "total", "percent"],
        "display": ["user", "path_id", "phase_idx", "phase_title", "score", "total",
                    "percent", "created_at"],
        "search": ["path_id", "phase_title"],
        "fk": ["user"],
    },
    "badges": {
        "model": Badge,
        "label": "Badges",
        "fields": ["user", "key"],
        "display": ["user", "key", "earned_at"],
        "search": ["key"],
        "fk": ["user"],
    },
    "milestoneprojects": {
        "model": MilestoneProject,
        "label": "Milestone projects",
        "fields": ["user", "path_id", "phase_idx", "phase_title", "title", "brief",
                   "acceptance_criteria", "starter_template", "rubric",
                   "submission_url", "submission_notes", "status", "ai_review", "ai_score"],
        "display": ["user", "path_id", "phase_idx", "title", "status", "ai_score", "updated_at"],
        "search": ["path_id", "title", "phase_title"],
        "fk": ["user"],
    },
    "skills": {
        "model": Skill,
        "label": "Skills",
        "fields": ["name", "slug", "description", "domain"],
        "display": ["name", "slug", "domain", "created_at"],
        "search": ["name", "slug", "domain"],
    },
    "resources": {
        "model": Resource,
        "label": "Resource catalog",
        "fields": ["name", "url", "type", "level", "cost", "duration_hours", "domain",
                   "description", "content_source", "url_health", "community_rating", "rating_count"],
        "display": ["name", "url", "type", "level", "cost", "content_source", "url_health",
                    "verified_at", "community_rating"],
        "search": ["name", "url", "domain"],
    },
}

PATHS_RESOURCE = {
    "label": "Paths",
    "fields": [
        {"name": "goal", "label": "Goal", "type": "string", "required": True},
        {"name": "content", "label": "Content (markdown or JSON)", "type": "text", "required": True},
        {"name": "format", "label": "Format", "type": "choice", "required": False,
         "choices": [{"value": "markdown", "label": "Markdown"},
                     {"value": "structured", "label": "Structured JSON"}]},
        {"name": "owner", "label": "Owner user id", "type": "string", "required": False},
        {"name": "current_level", "label": "Current level", "type": "string", "required": False},
        {"name": "hours_per_day", "label": "Hours per day", "type": "integer", "required": False},
        {"name": "months", "label": "Months", "type": "integer", "required": False},
    ],
    "display": ["goal", "created_at", "owner", "format", "version"],
    "search": ["goal"],
    "sortable": ["goal", "created_at", "format", "version"],
}


def _admin_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_superuser):
            return JsonResponse({"error": "Admin access required"}, status=403)
        return fn(request, *args, **kwargs)
    return wrapper


def _read_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Invalid JSON body")
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def _iso(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _field_type(field):
    if isinstance(field, models.ForeignKey):
        return "fk"
    if isinstance(field, models.BooleanField):
        return "boolean"
    if isinstance(field, models.FloatField):
        return "float"
    if isinstance(field, models.IntegerField):
        return "integer"
    if isinstance(field, models.DateTimeField):
        return "datetime"
    if isinstance(field, models.DateField):
        return "date"
    return "string"


def _field_required(field):
    if isinstance(field, models.AutoField):
        return False
    if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
        return False
    if field.has_default():
        return False
    return not (field.blank or field.null)


def _field_specs(spec):
    out = []
    for name in spec["fields"]:
        field = spec["model"]._meta.get_field(name)
        entry = {
            "name": name,
            "label": str(field.verbose_name),
            "type": _field_type(field),
            "required": _field_required(field),
            "nullable": bool(field.null),
        }
        if getattr(field, "choices", None):
            entry["choices"] = [{"value": value, "label": label} for value, label in field.choices]
        if isinstance(field, models.ForeignKey):
            entry["fk"] = "users"
        if name in spec.get("write_only", []):
            entry["write_only"] = True
            entry["required"] = spec.get("special") == "user"
        out.append(entry)
    return out


def _serialize(spec, obj, full=False):
    out = {"id": obj.pk}
    names = list(spec["display"])
    if full:
        names = list(dict.fromkeys(names + spec["fields"]))
    write_only = set(spec.get("write_only", []))
    for name in names:
        if name in write_only:
            continue
        if name in spec.get("fk", []):
            rel = getattr(obj, name)
            out[name] = rel.pk if rel else None
            out[f"{name}_label"] = str(rel) if rel else ""
        else:
            out[name] = _iso(getattr(obj, name))
    return out


def _assign(spec, obj, data):
    editable = set(spec["fields"])
    write_only = set(spec.get("write_only", []))
    fk_fields = spec.get("fk", [])
    errors = {}
    for key, value in data.items():
        if key == "id":
            continue
        if key not in editable:
            errors[key] = ["Not an editable field"]
            continue
        if key in write_only:
            continue
        if key in fk_fields:
            if value in (None, ""):
                setattr(obj, key, None)
                continue
            try:
                rel_pk = int(value)
            except (TypeError, ValueError):
                errors[key] = ["Invalid reference"]
                continue
            rel = User.objects.filter(pk=rel_pk).first()
            if rel is None:
                errors[key] = ["Referenced user does not exist"]
                continue
            setattr(obj, key, rel)
            continue
        if value is None:
            field = spec["model"]._meta.get_field(key)
            if field.null:
                setattr(obj, key, None)
            elif not field.has_default():
                setattr(obj, key, None)
            continue
        setattr(obj, key, value)
    return errors


def _clean_or_errors(obj):
    try:
        obj.full_clean()
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            return dict(exc.message_dict)
        return {"__all__": exc.messages}
    return None


def _list_view(spec, request):
    qs = spec["model"].objects.all()
    if spec.get("fk"):
        qs = qs.select_related(*spec["fk"])
    search = (request.GET.get("search") or "").strip()
    if search and spec.get("search"):
        query = Q()
        for name in spec["search"]:
            query |= Q(**{f"{name}__icontains": search})
        qs = qs.filter(query)
    sort = (request.GET.get("sort") or "").strip()
    if sort:
        if sort.lstrip("-") not in spec["display"]:
            return JsonResponse({"error": f"Cannot sort by '{sort}'"}, status=400)
        qs = qs.order_by(sort)
    else:
        qs = qs.order_by("-pk")
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = min(100, max(1, int(request.GET.get("page_size", "20"))))
    except ValueError:
        return JsonResponse({"error": "Invalid pagination parameters"}, status=400)
    total = qs.count()
    start = (page - 1) * page_size
    results = [_serialize(spec, obj) for obj in qs[start:start + page_size]]
    return JsonResponse({"count": total, "page": page, "page_size": page_size, "results": results})


def _create_view(spec, request):
    try:
        data = _read_json(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    obj = spec["model"]()
    errors = _assign(spec, obj, data)
    if spec.get("special") == "user":
        password = str(data.get("password") or "")
        if not password:
            errors.setdefault("password", ["Password is required"])
        elif len(password) < 6:
            errors.setdefault("password", ["Password must be at least 6 characters"])
        else:
            obj.set_password(password)
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    errors = _clean_or_errors(obj)
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    obj.save()
    return JsonResponse({"result": _serialize(spec, obj, full=True)}, status=201)


def _update_view(spec, obj, request):
    try:
        data = _read_json(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    errors = _assign(spec, obj, data)
    if spec.get("special") == "user":
        password = str(data.get("password") or "")
        if password and len(password) < 6:
            errors.setdefault("password", ["Password must be at least 6 characters"])
        elif password:
            obj.set_password(password)
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    errors = _clean_or_errors(obj)
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    obj.save()
    return JsonResponse({"result": _serialize(spec, obj, full=True)})


def _delete_view(spec, request, pk):
    if spec.get("special") == "user" and request.user.pk == pk:
        return JsonResponse({"error": "You cannot delete your own account"}, status=400)
    obj = spec["model"].objects.filter(pk=pk).first()
    if obj is None:
        return JsonResponse({"error": "Not found"}, status=404)
    obj.delete()
    return JsonResponse({"deleted": True, "id": pk})


def _get_object(spec, pk):
    qs = spec["model"].objects.filter(pk=pk)
    if spec.get("fk"):
        qs = qs.select_related(*spec["fk"])
    return qs.first()


@csrf_exempt
@require_http_methods(["GET", "POST"])
@_admin_required
def collection(request, resource):
    spec = RESOURCES.get(resource)
    if spec is None:
        return JsonResponse({"error": "Unknown resource"}, status=404)
    if request.method == "GET":
        return _list_view(spec, request)
    return _create_view(spec, request)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
@_admin_required
def item(request, resource, pk):
    spec = RESOURCES.get(resource)
    if spec is None:
        return JsonResponse({"error": "Unknown resource"}, status=404)
    if request.method == "GET":
        obj = _get_object(spec, pk)
        if obj is None:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse({"result": _serialize(spec, obj, full=True)})
    if request.method == "DELETE":
        return _delete_view(spec, request, pk)
    obj = spec["model"].objects.filter(pk=pk).first()
    if obj is None:
        return JsonResponse({"error": "Not found"}, status=404)
    return _update_view(spec, obj, request)


def _path_list_item(path):
    meta = path.get("metadata") or {}
    return {
        "id": path["id"],
        "goal": meta.get("goal", ""),
        "created_at": meta.get("created_at", ""),
        "owner": meta.get("owner", ""),
        "format": meta.get("format", "markdown"),
        "version": int(meta.get("version", 1) or 1),
        "source": meta.get("source", "agent"),
        "content_size": len(path.get("content") or ""),
    }


def _path_detail(path):
    meta = path.get("metadata") or {}
    out = _path_list_item(path)
    out["content"] = path.get("content") or ""
    out["current_level"] = meta.get("current_level", "")
    out["hours_per_day"] = meta.get("hours_per_day", "")
    out["months"] = meta.get("months", "")
    return out


def _path_meta(data, existing=None):
    meta = dict(existing or {})
    for key in ("goal", "format", "owner", "current_level", "hours_per_day", "months"):
        value = data.get(key)
        if value is None or value == "":
            if key in ("owner", "current_level", "hours_per_day", "months"):
                continue
            continue
        if key in ("hours_per_day", "months"):
            try:
                meta[key] = int(value)
            except (TypeError, ValueError):
                continue
        else:
            meta[key] = str(value)
    return meta


@csrf_exempt
@require_http_methods(["GET", "POST"])
@_admin_required
def paths_collection(request):
    if request.method == "GET":
        try:
            page = max(1, int(request.GET.get("page", "1")))
            page_size = min(100, max(1, int(request.GET.get("page_size", "20"))))
        except ValueError:
            return JsonResponse({"error": "Invalid pagination parameters"}, status=400)
        paths = vector_memory.get_recent_paths(n=200)
        search = (request.GET.get("search") or "").strip().lower()
        if search:
            paths = [p for p in paths if search in (p.get("metadata") or {}).get("goal", "").lower()]
        sort = (request.GET.get("sort") or "").strip()
        if sort == "goal":
            paths.sort(key=lambda p: (p.get("metadata") or {}).get("goal", "").lower())
        elif sort == "-goal":
            paths.sort(key=lambda p: (p.get("metadata") or {}).get("goal", "").lower(), reverse=True)
        elif sort in ("created_at", "-created_at"):
            paths.sort(key=lambda p: float((p.get("metadata") or {}).get("created_at", 0) or 0),
                       reverse=sort.startswith("-"))
        total = len(paths)
        start = (page - 1) * page_size
        results = [_path_list_item(p) for p in paths[start:start + page_size]]
        return JsonResponse({"count": total, "page": page, "page_size": page_size, "results": results})
    try:
        data = _read_json(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    goal = str(data.get("goal") or "").strip()
    content = str(data.get("content") or "").strip()
    errors = {}
    if not goal:
        errors["goal"] = ["Goal is required"]
    if not content:
        errors["content"] = ["Content is required"]
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    meta = _path_meta(data)
    meta.setdefault("format", "markdown")
    meta["source"] = "manual"
    doc_id = vector_memory.save_path(goal, content, meta)
    path = vector_memory.get_path(doc_id)
    return JsonResponse({"result": _path_detail(path)}, status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
@_admin_required
def path_item(request, doc_id):
    path = vector_memory.get_path(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    if request.method == "GET":
        return JsonResponse({"result": _path_detail(path)})
    if request.method == "DELETE":
        vector_memory.delete_path(doc_id)
        return JsonResponse({"deleted": True, "id": doc_id})
    try:
        data = _read_json(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    content = str(data.get("content") or "").strip()
    if not content:
        return JsonResponse({"errors": {"content": ["Content is required"]}}, status=400)
    goal = str(data.get("goal") or "").strip() or (path["metadata"].get("goal", "") or "")
    if not goal:
        return JsonResponse({"errors": {"goal": ["Goal is required"]}}, status=400)
    meta = _path_meta(data, existing=path.get("metadata"))
    meta["goal"] = goal
    vector_memory.update_path(doc_id, content, meta)
    updated = vector_memory.get_path(doc_id)
    return JsonResponse({"result": _path_detail(updated)})


@require_GET
@_admin_required
def admin_meta(request):
    resources = {}
    for name, spec in RESOURCES.items():
        resources[name] = {
            "label": spec["label"],
            "fields": _field_specs(spec),
            "display": spec["display"],
            "search": spec.get("search", []),
            "sortable": spec["display"],
        }
    resources["paths"] = PATHS_RESOURCE
    return JsonResponse({"resources": resources})


@require_GET
@_admin_required
def admin_counts(request):
    return JsonResponse({
        "users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "superusers": User.objects.filter(is_superuser=True).count(),
        "feedback": Feedback.objects.count(),
        "progress": PathProgress.objects.count(),
        "flashcards": Flashcard.objects.count(),
        "due_flashcards": Flashcard.objects.filter(due_at__lte=timezone.now()).count(),
        "activity": StudyActivity.objects.count(),
        "tests": TestResult.objects.count(),
        "badges": Badge.objects.count(),
        "paths": vector_memory.count_paths(),
    })

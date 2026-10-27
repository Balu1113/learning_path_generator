"""Study groups: private cohorts with an invite code and an optional shared roadmap."""
import secrets
import string

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from memory.vector_store import vector_memory
from .adaptive_views import _topic_total
from .models import GroupMembership, GroupDeadline, GroupCheckin, PathProgress, StudyActivity, StudyGroup
from .study_views import _load_path, _require_user
from .views import _json_body

CODE_ALPHABET = string.ascii_uppercase + string.digits  # no O/0/I/1/L
MAX_GROUPS_PER_USER = 50


def _new_code():
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not StudyGroup.objects.filter(code=code).exists():
            return code
    raise RuntimeError("Could not allocate a unique group code")


def _path_info(group):
    if not group.path_id:
        return None
    path = vector_memory.get_path(group.path_id)
    if path is None:
        return None
    meta = path["metadata"]
    return {
        "path_id": group.path_id,
        "goal": meta.get("goal", ""),
        "format": meta.get("format", "markdown"),
    }


def _summary(group, user):
    path_info = _path_info(group)
    return {
        "id": group.id,
        "name": group.name,
        "code": group.code,
        "owner_name": group.owner.username,
        "is_owner": group.owner_id == user.id,
        "member_count": group.memberships.count(),
        "created_at": group.created_at.isoformat(),
        "path_id": path_info["path_id"] if path_info else "",
        "path_goal": path_info["goal"] if path_info else "",
        "path_format": path_info["format"] if path_info else "",
    }


@require_GET
def groups_list(request):
    denied = _require_user(request)
    if denied:
        return denied
    rows = (GroupMembership.objects
            .filter(user=request.user)
            .select_related("group", "group__owner")
            .order_by("-group__created_at"))
    return JsonResponse({"groups": [_summary(r.group, request.user) for r in rows]})


@csrf_exempt
@require_POST
def groups_create(request):
    denied = _require_user(request)
    if denied:
        return denied
    name = (_json_body(request).get("name") or "").strip()[:80]
    if not name:
        return JsonResponse({"error": "Group name is required"}, status=400)
    if GroupMembership.objects.filter(user=request.user).count() >= MAX_GROUPS_PER_USER:
        return JsonResponse({"error": "You are in too many groups already"}, status=400)
    group = StudyGroup.objects.create(name=name, code=_new_code(), owner=request.user)
    GroupMembership.objects.create(group=group, user=request.user)
    return JsonResponse({"group": _summary(group, request.user), "created": True})


@csrf_exempt
@require_POST
def groups_join(request):
    denied = _require_user(request)
    if denied:
        return denied
    code = (_json_body(request).get("code") or "").strip().upper()
    if not code:
        return JsonResponse({"error": "Invite code is required"}, status=400)
    group = StudyGroup.objects.filter(code=code).select_related("owner").first()
    if group is None:
        return JsonResponse({"error": "No group found for that code"}, status=404)
    _, created = GroupMembership.objects.get_or_create(group=group, user=request.user)
    return JsonResponse({"group": _summary(group, request.user), "joined": created})


@require_GET
def group_detail(request, group_id):
    denied = _require_user(request)
    if denied:
        return denied
    group = StudyGroup.objects.filter(id=group_id).select_related("owner").first()
    if group is None:
        return JsonResponse({"error": "Group not found"}, status=404)
    is_member = GroupMembership.objects.filter(group=group, user=request.user).exists()
    if not is_member:
        return JsonResponse({"error": "Not a member of this group"}, status=403)

    path_info = _path_info(group)
    total = 0
    if path_info and path_info["format"] == "structured":
        path = vector_memory.get_path(group.path_id)
        total = _topic_total(path) if path else 0

    members = []
    for m in (GroupMembership.objects
              .filter(group=group)
              .select_related("user")
              .order_by("joined_at")):
        done = 0
        if group.path_id:
            done = PathProgress.objects.filter(
                user=m.user, path_id=group.path_id,
                item_key__startswith="t:", done=True,
            ).count()
        last_active = (StudyActivity.objects
                       .filter(user=m.user)
                       .order_by("-date")
                       .values_list("date", flat=True)
                       .first())
        members.append({
            "id": m.user.id,
            "username": m.user.username,
            "is_owner": m.user_id == group.owner_id,
            "joined_at": m.joined_at.isoformat(),
            "last_active": last_active.isoformat() if last_active else None,
            "progress": {
                "done": done,
                "total": total,
                "percent": min(100, round(100 * done / total)) if total else None,
            },
        })
    return JsonResponse({**_summary(group, request.user), "members": members})


@csrf_exempt
@require_POST
def group_set_path(request, group_id):
    """Owner-only: attach (or clear with path_id:"") the group's shared roadmap."""
    denied = _require_user(request)
    if denied:
        return denied
    group = StudyGroup.objects.filter(id=group_id).select_related("owner").first()
    if group is None:
        return JsonResponse({"error": "Group not found"}, status=404)
    if group.owner_id != request.user.id:
        return JsonResponse({"error": "Only the group owner can change the roadmap"}, status=403)
    path_id = (_json_body(request).get("path_id") or "").strip()
    if not path_id:
        group.path_id = ""
        group.save(update_fields=["path_id"])
        return JsonResponse({**_summary(group, request.user), "path_id": ""})
    _, err = _load_path(request, path_id)
    if err:
        return err
    group.path_id = path_id
    group.save(update_fields=["path_id"])
    return JsonResponse(_summary(group, request.user))


@csrf_exempt
@require_POST
def group_leave(request, group_id):
    denied = _require_user(request)
    if denied:
        return denied
    group = StudyGroup.objects.filter(id=group_id).select_related("owner").first()
    if group is None:
        return JsonResponse({"error": "Group not found"}, status=404)
    membership = GroupMembership.objects.filter(group=group, user=request.user).first()
    if membership is None:
        return JsonResponse({"error": "Not a member of this group"}, status=403)
    was_owner = group.owner_id == request.user.id
    membership.delete()
    if was_owner:
        successor = (GroupMembership.objects
                     .filter(group=group)
                     .order_by("joined_at")
                     .select_related("user")
                     .first())
        if successor:
            group.owner = successor.user
            group.save(update_fields=["owner"])
        else:
            group.delete()
            return JsonResponse({"left": True, "group_deleted": True})
    return JsonResponse({"left": True, "group_deleted": False})


# -------------------------------------------------------------------------
# Cohort features: shared deadlines and accountability check-ins
# -------------------------------------------------------------------------

@csrf_exempt
@require_POST
def group_set_deadline(request, group_id):
    """Owner or member: create a shared deadline for the group."""
    denied = _require_user(request)
    if denied:
        return denied
    group = StudyGroup.objects.filter(id=group_id).first()
    if group is None:
        return JsonResponse({"error": "Group not found"}, status=404)
    if not GroupMembership.objects.filter(group=group, user=request.user).exists():
        return JsonResponse({"error": "Not a member of this group"}, status=403)
    data = _json_body(request)
    title = (data.get("title") or "").strip()[:200]
    due_raw = (data.get("due_date") or "").strip()
    description = (data.get("description") or "").strip()
    if not title or not due_raw:
        return JsonResponse({"error": "title and due_date are required"}, status=400)
    try:
        due_date = date.fromisoformat(due_raw[:10])
    except ValueError:
        return JsonResponse({"error": "due_date must be YYYY-MM-DD"}, status=400)
    deadline = GroupDeadline.objects.create(
        group=group,
        title=title,
        due_date=due_date,
        description=description,
        created_by=request.user,
    )
    return JsonResponse({
        "id": deadline.id,
        "title": deadline.title,
        "due_date": deadline.due_date.isoformat(),
        "description": deadline.description,
        "created_at": deadline.created_at.isoformat(),
    })


@csrf_exempt
@require_POST
def group_checkin(request, group_id):
    """Member: post a brief accountability check-in."""
    denied = _require_user(request)
    if denied:
        return denied
    group = StudyGroup.objects.filter(id=group_id).first()
    if group is None:
        return JsonResponse({"error": "Group not found"}, status=404)
    if not GroupMembership.objects.filter(group=group, user=request.user).exists():
        return JsonResponse({"error": "Not a member of this group"}, status=403)
    data = _json_body(request)
    message = (data.get("message") or "").strip()[:2000]
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)
    checkin = GroupCheckin.objects.create(
        group=group,
        user=request.user,
        message=message,
    )
    return JsonResponse({
        "id": checkin.id,
        "message": checkin.message,
        "username": request.user.username,
        "created_at": checkin.created_at.isoformat(),
    })


@require_GET
def group_checkins(request, group_id):
    """List recent check-ins for a group (newest first)."""
    denied = _require_user(request)
    if denied:
        return denied
    group = StudyGroup.objects.filter(id=group_id).first()
    if group is None:
        return JsonResponse({"error": "Group not found"}, status=404)
    if not GroupMembership.objects.filter(group=group, user=request.user).exists():
        return JsonResponse({"error": "Not a member of this group"}, status=403)
    try:
        limit = max(1, min(50, int(request.GET.get("limit", 20))))
    except (TypeError, ValueError):
        limit = 20
    checkins = [
        {
            "id": c.id,
            "username": c.user.username,
            "message": c.message,
            "created_at": c.created_at.isoformat(),
        }
        for c in GroupCheckin.objects.filter(group=group).select_related("user")[:limit]
    ]
    return JsonResponse({"checkins": checkins, "count": len(checkins)})

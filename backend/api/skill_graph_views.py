import json
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Skill, SkillEdge, SkillMastery, PathSkill
from .views import _path_or_none, _can_access


def _load_path(request, doc_id):
    path = _path_or_none(doc_id)
    if path is None:
        return None, JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return None, JsonResponse({"error": "Not allowed"}, status=403)
    return path, None


def _require_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    return None


def _path_skill_ids(user, doc_id):
    return set(
        PathSkill.objects.filter(user=user, path_id=doc_id).values_list("skill_id", flat=True)
    )


def _phase_titles(path):
    """Phase titles from a path document (structured JSON or markdown)."""
    try:
        phases = json.loads(path["content"]).get("phases", [])
    except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
        phases = []
    return [p.get("title") or f"Phase {i + 1}" for i, p in enumerate(phases) if isinstance(p, dict)]


def _phase_name(titles, idx):
    if idx is not None and 0 <= idx < len(titles):
        return titles[idx]
    return f"Phase {idx + 1}" if idx is not None else "this path"


@require_GET
def skill_graph(request, doc_id):
    """Skill dependency graph for a path: deduped nodes + SkillEdge-based edges."""
    denied = _require_user(request)
    if denied:
        return denied
    path, error = _load_path(request, doc_id)
    if error:
        return error

    path_skills = PathSkill.objects.filter(
        user=request.user, path_id=doc_id
    ).select_related("skill")

    mastery = {
        m.skill_id: m
        for m in SkillMastery.objects.filter(user=request.user).select_related("skill")
    }

    nodes_by_id = {}
    for ps in path_skills:
        skill = ps.skill
        entry = nodes_by_id.get(skill.id)
        if entry is None:
            m = mastery.get(skill.id)
            entry = {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "domain": skill.domain,
                "state": m.state if m else "unassessed",
                "score": m.score if m else None,
                "phase": ps.phase_idx,
                "topics": [],
            }
            nodes_by_id[skill.id] = entry
        entry["phase"] = min(entry["phase"], ps.phase_idx if ps.phase_idx is not None else entry["phase"])
        if ps.topic_title and ps.topic_title not in entry["topics"]:
            entry["topics"].append(ps.topic_title)

    skill_ids = set(nodes_by_id)
    edges = [
        {"from": e.from_skill_id, "to": e.to_skill_id}
        for e in SkillEdge.objects.filter(
            from_skill_id__in=skill_ids, to_skill_id__in=skill_ids
        )
    ]

    return JsonResponse({
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
    })


@require_GET
def phase_blockers(request, doc_id):
    """Phase-level warnings derived live from prerequisite edges."""
    denied = _require_user(request)
    if denied:
        return denied
    path, error = _load_path(request, doc_id)
    if error:
        return error

    titles = _phase_titles(path)

    skill_phases = {}
    for skill_id, phase in PathSkill.objects.filter(
        user=request.user, path_id=doc_id
    ).values_list("skill_id", "phase_idx"):
        skill_phases.setdefault(skill_id, set()).add(phase or 0)

    path_skill_ids = set(skill_phases)
    if not path_skill_ids:
        return JsonResponse({"warnings": []})

    warnings = []
    seen = set()
    in_edges = SkillEdge.objects.filter(
        to_skill_id__in=path_skill_ids
    ).select_related("from_skill", "to_skill")

    for edge in in_edges:
        to_phases = skill_phases[edge.to_skill_id]
        from_phases = skill_phases.get(edge.from_skill_id)

        if from_phases is None:
            # Prerequisite skill is not part of this path at all
            key = ("missing", edge.from_skill_id, edge.to_skill_id)
            if key in seen:
                continue
            seen.add(key)
            warnings.append({
                "type": "missing_prerequisite",
                "blocking_phase": None,
                "blocked_phase": min(to_phases),
                "message": (
                    f"{edge.to_skill.name} requires {edge.from_skill.name}, "
                    "which is not covered in this path"
                ),
            })
            continue

        from_min = min(from_phases)
        to_min = min(to_phases)
        if from_min > to_min:
            # A skill needed early is only introduced in a later phase
            key = ("inversion", edge.from_skill_id, edge.to_skill_id)
            if key in seen:
                continue
            seen.add(key)
            warnings.append({
                "type": "phase_inversion",
                "blocking_phase": from_min,
                "blocked_phase": to_min,
                "message": (
                    f"{_phase_name(titles, to_min)} needs {edge.from_skill.name}, "
                    f"first covered in {_phase_name(titles, from_min)} — "
                    "consider reordering those topics"
                ),
            })

    return JsonResponse({"warnings": warnings[:20]})


@require_GET
def critical_path(request, doc_id):
    """Skills other path skills depend on most (computed live from SkillEdge)."""
    denied = _require_user(request)
    if denied:
        return denied
    path, error = _load_path(request, doc_id)
    if error:
        return error

    titles = _phase_titles(path)
    path_skill_ids = _path_skill_ids(request.user, doc_id)
    if not path_skill_ids:
        return JsonResponse({"critical_skills": [], "total_critical": 0})

    in_counts = dict(
        SkillEdge.objects.filter(to_skill_id__in=path_skill_ids)
        .values("to_skill_id").annotate(c=Count("id"))
        .values_list("to_skill_id", "c")
    )
    internal_out = dict(
        SkillEdge.objects.filter(
            from_skill_id__in=path_skill_ids, to_skill_id__in=path_skill_ids
        )
        .values("from_skill_id").annotate(c=Count("id"))
        .values_list("from_skill_id", "c")
    )

    phase_by_skill = {}
    topics_by_skill = {}
    for skill_id, phase, topic in PathSkill.objects.filter(
        user=request.user, path_id=doc_id
    ).values_list("skill_id", "phase_idx", "topic_title"):
        if skill_id not in phase_by_skill or (phase or 0) < phase_by_skill[skill_id]:
            phase_by_skill[skill_id] = phase or 0
        if topic and topic not in topics_by_skill.setdefault(skill_id, []):
            topics_by_skill[skill_id].append(topic)

    skills_by_id = {
        s.id: s for s in Skill.objects.filter(id__in=path_skill_ids)
    }

    critical_skills = []
    for skill_id in path_skill_ids:
        unlocks = internal_out.get(skill_id, 0)
        if unlocks <= 0:
            continue
        skill = skills_by_id.get(skill_id)
        if skill is None:
            continue
        phase = phase_by_skill.get(skill_id, 0)
        critical_skills.append({
            "skill_id": skill_id,
            "skill": skill.name,
            "phase": phase,
            "phase_title": _phase_name(titles, phase),
            "topic": (topics_by_skill.get(skill_id) or [""])[0],
            "prerequisite_count": in_counts.get(skill_id, 0),
            "unlocks_count": unlocks,
        })

    critical_skills.sort(key=lambda x: (-x["unlocks_count"], x["phase"], x["skill"]))

    return JsonResponse({
        "critical_skills": critical_skills,
        "total_critical": len(critical_skills),
    })


@require_GET
def skill_mastery_status(request):
    """Get user's skill mastery status across all paths."""
    denied = _require_user(request)
    if denied:
        return denied

    mastery = SkillMastery.objects.filter(user=request.user).select_related("skill")

    return JsonResponse({
        "mastery": [
            {
                "skill": m.skill.name,
                "state": m.state,
                "score": m.score,
                "evidence_count": m.evidence_count,
                "last_evidence": m.last_evidence_at.isoformat() if m.last_evidence_at else None,
            }
            for m in mastery
        ]
    })


@require_GET
def skill_prerequisites(request, skill_id):
    """Get prerequisites for a specific skill (real SkillEdge data)."""
    denied = _require_user(request)
    if denied:
        return denied

    try:
        skill = Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return JsonResponse({"error": "Skill not found"}, status=404)

    prerequisites = SkillEdge.objects.filter(
        to_skill=skill
    ).select_related("from_skill")

    return JsonResponse({
        "skill": skill.name,
        "prerequisites": [
            {
                "id": p.from_skill.id,
                "name": p.from_skill.name,
                "domain": p.from_skill.domain,
            }
            for p in prerequisites
        ],
    })


@require_GET
def skill_unlocks(request, skill_id):
    """Get skills unlocked by mastering a skill (real SkillEdge data)."""
    denied = _require_user(request)
    if denied:
        return denied

    try:
        skill = Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return JsonResponse({"error": "Skill not found"}, status=404)

    unlocks = SkillEdge.objects.filter(
        from_skill=skill
    ).select_related("to_skill")

    return JsonResponse({
        "skill": skill.name,
        "unlocks": [
            {
                "id": u.to_skill.id,
                "name": u.to_skill.name,
                "domain": u.to_skill.domain,
            }
            for u in unlocks
        ],
    })

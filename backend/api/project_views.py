"""Project-based milestones: per-phase capstone projects with submissions and AI review."""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from datetime import datetime, timezone

from chains.path_generator import generate_phase_project, review_phase_project
from .models import MilestoneProject
from .progress_stats import record_activity
from .badges import evaluate as evaluate_badges
from .study_views import _load_path, _require_user
from .views import _json_body, _workspace_data

MAX_PHASES_PER_GENERATE = 12


def _project_payload(p):
    return {
        "id": p.id,
        "path_id": p.path_id,
        "phase_idx": p.phase_idx,
        "phase_title": p.phase_title,
        "title": p.title,
        "brief": p.brief,
        "acceptance_criteria": p.acceptance_criteria or [],
        "starter_template": p.starter_template,
        "rubric": p.rubric or [],
        "submission_url": p.submission_url,
        "submission_notes": p.submission_notes,
        "status": p.status,
        "ai_review": p.ai_review,
        "ai_score": p.ai_score,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


def _clean_project_spec(raw):
    """Validate the LLM project JSON; return a sanitized dict or None."""
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    brief = str(raw.get("brief") or "").strip()
    if not title or not brief:
        return None
    criteria = [str(c).strip() for c in (raw.get("acceptance_criteria") or []) if str(c).strip()]
    rubric = []
    for r in (raw.get("rubric") or []):
        if not isinstance(r, dict):
            continue
        name = str(r.get("criterion") or "").strip()
        if not name:
            continue
        try:
            points = int(r.get("max_points", 0))
        except (TypeError, ValueError):
            points = 0
        rubric.append({
            "criterion": name,
            "max_points": max(0, points),
            "description": str(r.get("description") or "").strip(),
        })
    return {
        "title": title[:255],
        "brief": brief,
        "acceptance_criteria": criteria[:10],
        "starter_template": str(raw.get("starter_template") or "").strip(),
        "rubric": rubric[:8],
    }


def _phase_context(ws, phase_idx):
    phases = (ws or {}).get("phases") or []
    if phase_idx < 0 or phase_idx >= len(phases):
        return None
    phase = phases[phase_idx]
    topics = phase.get("topics") or []
    return {
        "title": phase.get("title") or f"Phase {phase_idx + 1}",
        "description": phase.get("description") or "",
        "topics_text": "\n".join(
            f"- {t.get('title', '')}: {t.get('details', '')}" for t in topics if t.get("title")
        ) or "- (general phase knowledge)",
        "weeks": phase.get("estimated_weeks") or 4,
    }


@csrf_exempt
@require_POST
def projects_generate(request, doc_id):
    """Generate the capstone project for one phase, or for every phase that lacks one."""
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err

    ws = _workspace_data(path)
    phases = (ws or {}).get("phases") or []
    if not phases:
        return JsonResponse({"error": "No phases found in this path."}, status=400)

    data = _json_body(request)
    force = bool(data.get("force", False))
    raw_idx = data.get("phase_idx")
    if raw_idx is None:
        indices = list(range(min(len(phases), MAX_PHASES_PER_GENERATE)))
    else:
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            return JsonResponse({"error": "phase_idx must be an integer"}, status=400)
        if idx < 0 or idx >= len(phases):
            return JsonResponse({"error": "Phase not found"}, status=404)
        indices = [idx]

    goal = path["metadata"].get("goal", "learning")
    level = path["metadata"].get("current_level", "beginner")

    created = 0
    updated = 0
    existing = 0
    failed = 0
    projects = []
    for i in indices:
        ctx = _phase_context(ws, i)
        if ctx is None:
            continue
        row = MilestoneProject.objects.filter(user=request.user, path_id=doc_id, phase_idx=i).first()
        if row and not force:
            existing += 1
            projects.append(_project_payload(row))
            continue
        try:
            spec = _clean_project_spec(generate_phase_project(
                goal=goal,
                phase={
                    "title": ctx["title"],
                    "description": ctx["description"],
                    "topics_text": ctx["topics_text"],
                },
                current_level=level,
                weeks=ctx["weeks"],
            ))
        except Exception:
            spec = None
        if spec is None:
            failed += 1
            continue
        if row:
            for key, value in spec.items():
                setattr(row, key, value)
            row.submission_url = ""
            row.submission_notes = ""
            row.status = "draft"
            row.ai_review = ""
            row.ai_score = None
            row.reviewed_at = None
            row.phase_title = ctx["title"]
            row.save()
            updated += 1
        else:
            row = MilestoneProject.objects.create(
                user=request.user,
                path_id=doc_id,
                phase_idx=i,
                phase_title=ctx["title"],
                status="draft",
                **spec,
            )
            created += 1
        projects.append(_project_payload(row))

    if not projects and failed:
        return JsonResponse({"error": "The model returned an invalid project; nothing was saved."}, status=502)
    return JsonResponse({
        "created": created,
        "updated": updated,
        "existing": existing,
        "failed": failed,
        "projects": projects,
    })


@require_GET
def projects_list(request, doc_id):
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    rows = MilestoneProject.objects.filter(user=request.user, path_id=doc_id).order_by("phase_idx")
    projects = [_project_payload(p) for p in rows]
    reviewed = sum(1 for p in projects if p["status"] == "reviewed")
    return JsonResponse({
        "projects": projects,
        "total": len(projects),
        "reviewed": reviewed,
        "goal": path["metadata"].get("goal", ""),
    })


def _get_project_or_404(request, doc_id, phase_idx):
    return MilestoneProject.objects.filter(
        user=request.user, path_id=doc_id, phase_idx=phase_idx,
    ).first()


@require_GET
def projects_detail(request, doc_id, phase_idx):
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    row = _get_project_or_404(request, doc_id, phase_idx)
    if row is None:
        return JsonResponse({"error": "Project not found"}, status=404)
    return JsonResponse({"project": _project_payload(row)})


@csrf_exempt
@require_POST
def projects_submit(request, doc_id, phase_idx):
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    row = _get_project_or_404(request, doc_id, phase_idx)
    if row is None:
        return JsonResponse({"error": "Project not found"}, status=404)

    data = _json_body(request)
    url = str(data.get("submission_url") or "").strip()
    notes = str(data.get("submission_notes") or "").strip()
    if not url and not notes:
        return JsonResponse({"error": "Provide a submission URL, notes, or both."}, status=400)
    if url and not (url.startswith("http://") or url.startswith("https://")):
        return JsonResponse({"error": "submission_url must start with http:// or https://"}, status=400)

    row.submission_url = url[:500]
    row.submission_notes = notes[:8000]
    row.status = "submitted"
    row.ai_review = ""
    row.ai_score = None
    row.reviewed_at = None
    row.save(update_fields=[
        "submission_url", "submission_notes", "status",
        "ai_review", "ai_score", "reviewed_at", "updated_at",
    ])
    record_activity(request.user, "project")
    return JsonResponse({"project": _project_payload(row)})


@csrf_exempt
@require_POST
def projects_review(request, doc_id, phase_idx):
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    row = _get_project_or_404(request, doc_id, phase_idx)
    if row is None:
        return JsonResponse({"error": "Project not found"}, status=404)
    if row.status != "submitted":
        return JsonResponse({"error": "Submit the project before requesting an AI review."}, status=400)

    try:
        result = review_phase_project(
            brief=row.brief,
            acceptance_criteria=row.acceptance_criteria or [],
            rubric=row.rubric or [],
            submission_url=row.submission_url,
            submission_notes=row.submission_notes,
            title=row.title,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    review_text = str(result.get("review") or "").strip()
    if not review_text:
        return JsonResponse({"error": "The reviewer returned empty feedback. Try again."}, status=502)
    try:
        score = int(result.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    criteria_met = [str(c).strip() for c in (result.get("criteria_met") or []) if str(c).strip()]
    criteria_missed = []
    for c in (result.get("criteria_missed") or []):
        if isinstance(c, dict) and c.get("criterion"):
            criteria_missed.append({
                "criterion": str(c.get("criterion")).strip(),
                "why": str(c.get("why") or "").strip(),
            })
        elif isinstance(c, str) and c.strip():
            criteria_missed.append({"criterion": c.strip(), "why": ""})

    row.ai_review = review_text
    row.ai_score = score
    row.status = "reviewed"
    row.reviewed_at = datetime.now(tz=timezone.utc)
    row.save(update_fields=["ai_review", "ai_score", "status", "reviewed_at", "updated_at"])

    try:
        from .skill_graph import record_skill_evidence
        record_skill_evidence(request.user, doc_id, phase_idx, score, strong=score >= 70)
    except Exception:
        pass

    record_activity(request.user, "project")
    badges = evaluate_badges(request.user)
    return JsonResponse({
        "project": _project_payload(row),
        "score": score,
        "criteria_met": criteria_met,
        "criteria_missed": criteria_missed,
        "badges": badges,
    })

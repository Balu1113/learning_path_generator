"""Evidence-based portfolio (Skill Passport), job-target gap analysis, and AI practice modes."""
import json
from datetime import date, timezone
from datetime import datetime as dt

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_GET, require_POST

from chains.path_generator import analyze_job_target, practice_turn
from memory.vector_store import vector_memory
from .models import (
    FocusSession, MilestoneProject, PortfolioSettings, SkillMastery, TestResult,
)
from .skill_graph import mastery_map
from .study_views import _load_path, _require_user
from .views import _json_body, _workspace_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_settings(user):
    obj, _ = PortfolioSettings.objects.get_or_create(user=user)
    return obj


def _settings_payload(ps):
    return {
        "is_public": ps.is_public,
        "show_projects": ps.show_projects,
        "show_test_scores": ps.show_test_scores,
        "show_study_hours": ps.show_study_hours,
    }


def _build_passport(user, settings):
    """Assemble the full Skill Passport dict for a user."""
    mastery = SkillMastery.objects.filter(user=user).select_related("skill").order_by(
        "-state", "-score"
    )
    skills = [
        {
            "name": m.skill.name,
            "slug": m.skill.slug,
            "domain": m.skill.domain,
            "state": m.state,
            "score": m.score,
            "evidence_count": m.evidence_count,
            "last_evidence_at": m.last_evidence_at.isoformat() if m.last_evidence_at else None,
        }
        for m in mastery
    ]

    projects = []
    if settings.show_projects:
        for p in MilestoneProject.objects.filter(user=user, status="reviewed").order_by("-reviewed_at"):
            projects.append({
                "title": p.title,
                "phase_title": p.phase_title,
                "score": p.ai_score,
                "submission_url": p.submission_url,
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
            })

    test_results = []
    if settings.show_test_scores:
        for r in TestResult.objects.filter(user=user).order_by("-created_at")[:20]:
            test_results.append({
                "phase_title": r.phase_title,
                "percent": r.percent,
                "score": r.score,
                "total": r.total,
                "date": r.created_at.date().isoformat(),
            })

    study_hours = None
    if settings.show_study_hours:
        total_seconds = sum(
            FocusSession.objects.filter(user=user).values_list("seconds", flat=True)
        )
        study_hours = round(total_seconds / 3600, 1)

    validated = [s for s in skills if s["state"] == "validated"]
    developing = [s for s in skills if s["state"] == "developing"]

    return {
        "username": user.username,
        "validated_count": len(validated),
        "developing_count": len(developing),
        "skills": skills,
        "projects": projects,
        "test_results": test_results,
        "study_hours": study_hours,
        "generated_at": dt.now(tz=timezone.utc).isoformat(),
    }


def _passport_markdown(passport, settings):
    lines = [
        f"# Skill Passport — {passport['username']}",
        f"*Generated {passport['generated_at'][:10]}*",
        "",
        f"**{passport['validated_count']}** validated skills · "
        f"**{passport['developing_count']}** developing",
    ]
    if settings.show_study_hours and passport["study_hours"] is not None:
        lines.append(f"**{passport['study_hours']}h** total study time")
    lines += ["", "## Validated Skills", ""]
    for s in passport["skills"]:
        if s["state"] == "validated":
            lines.append(f"- ✅ **{s['name']}** ({s['domain']}) — best score {s['score']}%")
    lines += ["", "## Developing Skills", ""]
    for s in passport["skills"]:
        if s["state"] == "developing":
            lines.append(f"- 🔄 **{s['name']}** ({s['domain']})")
    if settings.show_projects and passport["projects"]:
        lines += ["", "## Shipped Projects", ""]
        for p in passport["projects"]:
            url_part = f" — [{p['submission_url']}]({p['submission_url']})" if p["submission_url"] else ""
            lines.append(
                f"- **{p['title']}** ({p['phase_title']}) · score {p['score']}/100{url_part}"
            )
    if settings.show_test_scores and passport["test_results"]:
        lines += ["", "## Phase Test Results", ""]
        for r in passport["test_results"]:
            lines.append(f"- {r['date']} · {r['phase_title']} · {r['percent']}% ({r['score']}/{r['total']})")
    lines += ["", "---", "*Exported from LearnPath*"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Portfolio endpoints
# ---------------------------------------------------------------------------

@require_GET
def portfolio(request):
    """Return the authenticated user's full Skill Passport + privacy settings."""
    denied = _require_user(request)
    if denied:
        return denied
    settings = _get_or_create_settings(request.user)
    return JsonResponse({
        "passport": _build_passport(request.user, settings),
        "settings": _settings_payload(settings),
    })


@require_GET
def portfolio_public(request, username):
    """Public read-only Skill Passport for a user who has enabled public sharing."""
    from django.contrib.auth.models import User
    target = User.objects.filter(username=username).first()
    if target is None:
        return JsonResponse({"error": "User not found"}, status=404)
    try:
        settings = target.portfolio_settings
    except PortfolioSettings.DoesNotExist:
        return JsonResponse({"error": "This portfolio is not public"}, status=403)
    if not settings.is_public:
        return JsonResponse({"error": "This portfolio is not public"}, status=403)
    return JsonResponse({"passport": _build_passport(target, settings)})


@require_GET
def portfolio_export(request):
    """Download the authenticated user's Skill Passport as Markdown."""
    denied = _require_user(request)
    if denied:
        return denied
    settings = _get_or_create_settings(request.user)
    passport = _build_passport(request.user, settings)
    md = _passport_markdown(passport, settings)
    resp = HttpResponse(md, content_type="text/markdown; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="skill-passport-{request.user.username}.md"'
    return resp


@csrf_protect
@require_POST
def portfolio_privacy(request):
    """Update privacy settings for the authenticated user's portfolio."""
    denied = _require_user(request)
    if denied:
        return denied
    data = _json_body(request)
    settings = _get_or_create_settings(request.user)
    bool_fields = ("is_public", "show_projects", "show_test_scores", "show_study_hours")
    updates = []
    for field in bool_fields:
        if field in data:
            setattr(settings, field, bool(data[field]))
            updates.append(field)
    if updates:
        settings.save(update_fields=updates + ["updated_at"])
    return JsonResponse({"settings": _settings_payload(settings)})


# ---------------------------------------------------------------------------
# Job-target gap analysis
# ---------------------------------------------------------------------------

@csrf_protect
@require_POST
def job_target(request):
    """Extract required skills from a job description and compare with the learner's mastery."""
    denied = _require_user(request)
    if denied:
        return denied
    data = _json_body(request)
    jd = (data.get("job_description") or "").strip()[:5000]
    if not jd or len(jd) < 50:
        return JsonResponse({"error": "Job description must be at least 50 characters"}, status=400)

    mastery = mastery_map(request.user)
    validated = [slug for slug, m in mastery.items() if m.state == "validated"]
    developing = [slug for slug, m in mastery.items() if m.state == "developing"]

    try:
        result = analyze_job_target(jd, validated, developing)
    except Exception as e:
        return JsonResponse({"error": "Analysis failed"}, status=500)

    if not isinstance(result, dict) or not result.get("required_skills"):
        return JsonResponse({"error": "Analysis returned invalid data"}, status=502)

    mastery_by_slug = {slug: m.state for slug, m in mastery.items()}
    for skill in result.get("required_skills") or []:
        slug = skill.get("slug", "")
        skill["learner_state"] = mastery_by_slug.get(slug, "unassessed")

    gap_skills = [
        s for s in result.get("required_skills") or []
        if s.get("learner_state") != "validated"
    ]
    result["gap_count"] = len(gap_skills)
    result["gap_skills"] = gap_skills
    result["ready_count"] = len(result.get("required_skills") or []) - len(gap_skills)
    return JsonResponse(result)


# ---------------------------------------------------------------------------
# AI practice modes
# ---------------------------------------------------------------------------

VALID_SCENARIOS = {"mock_interview", "debugging", "code_review", "architecture", "stakeholder"}
SCENARIO_LABELS = {
    "mock_interview": "Mock Interview",
    "debugging": "Debugging Session",
    "code_review": "Code Review",
    "architecture": "Architecture Review",
    "stakeholder": "Stakeholder Conversation",
}


@csrf_protect
@require_POST
def practice(request, doc_id):
    """Run one turn of an AI practice scenario grounded in the path's topics."""
    path, err = _load_path(request, doc_id)
    if err:
        return err

    data = _json_body(request)
    scenario = (data.get("scenario") or "mock_interview").strip().lower()[:50]
    if scenario not in VALID_SCENARIOS:
        return JsonResponse(
            {"error": f"Invalid scenario"},
            status=400,
        )
    message = (data.get("message") or "").strip()[:2000]
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)
    history = data.get("history") or []
    if not isinstance(history, list):
        history = []
    history = history[:20]

    ws = _workspace_data(path)
    phase_idx = data.get("phase_idx")
    try:
        phase_idx = int(phase_idx) if phase_idx is not None else None
    except (TypeError, ValueError):
        phase_idx = None

    phases = (ws or {}).get("phases") or []
    if phase_idx is not None and 0 <= phase_idx < len(phases):
        phase = phases[phase_idx]
        topics_text = "\n".join(
            f"- {t.get('title', '')}: {t.get('details', '')}"
            for t in (phase.get("topics") or [])
            if t.get("title")
        ) or "- (general phase knowledge)"
    else:
        topics_text = "\n".join(
            f"- {t.get('title', '')}"
            for ph in phases
            for t in (ph.get("topics") or [])
            if t.get("title")
        )[:3000] or "- (general roadmap knowledge)"

    goal = path["metadata"].get("goal", "this learning path")[:500]
    try:
        reply = practice_turn(
            scenario=scenario,
            goal=goal,
            topics=topics_text,
            message=message,
            history=history,
        )
    except Exception as e:
        return JsonResponse({"error": "Practice session failed"}, status=500)

    return JsonResponse({
        "reply": reply,
        "scenario": scenario,
        "scenario_label": SCENARIO_LABELS[scenario],
    })

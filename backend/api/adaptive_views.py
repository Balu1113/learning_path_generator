"""Adaptive intelligence: focus (Pomodoro) sessions, deadline risk alerts, phase retuning."""
import json
from datetime import date, datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from chains.path_generator import _parse_json, parse_markdown_phases
from memory.vector_store import vector_memory
from .models import FocusSession, MilestoneProject, PathProgress, TestResult
from .progress_stats import record_activity
from .study_views import _load_path, _require_user
from .views import _copy_progress, _get_llm, _json_body, _version_meta

MAX_FOCUS_SECONDS = 4 * 3600
MIN_FOCUS_SECONDS = 30


def _today_focus_seconds(qs):
    return sum(qs.filter(created_at__date=date.today()).values_list("seconds", flat=True))


@csrf_exempt
@require_POST
def focus_log(request):
    denied = _require_user(request)
    if denied:
        return denied
    data = _json_body(request)
    path_id = (data.get("path_id") or "").strip()
    if not path_id:
        return JsonResponse({"error": "path_id is required"}, status=400)
    try:
        seconds = int(data.get("seconds", 0))
    except (TypeError, ValueError):
        seconds = 0
    if seconds < MIN_FOCUS_SECONDS:
        return JsonResponse({"error": "Session too short to log (minimum 30 seconds)"}, status=400)
    seconds = min(seconds, MAX_FOCUS_SECONDS)
    path, err = _load_path(request, path_id)
    if err:
        return err
    try:
        phase_idx = int(data.get("phase_idx", 0))
    except (TypeError, ValueError):
        phase_idx = 0
    phase_title = str(data.get("phase_title") or "")[:255]
    FocusSession.objects.create(
        user=request.user,
        path_id=path_id,
        phase_idx=max(0, phase_idx),
        phase_title=phase_title,
        seconds=seconds,
    )
    record_activity(request.user, "focus")
    scope = FocusSession.objects.filter(user=request.user, path_id=path_id)
    return JsonResponse({
        "ok": True,
        "logged_seconds": seconds,
        "today_seconds": _today_focus_seconds(scope),
        "path_seconds": sum(scope.values_list("seconds", flat=True)),
    })


@require_GET
def focus_summary(request):
    denied = _require_user(request)
    if denied:
        return denied
    path_id = (request.GET.get("path_id") or "").strip()
    qs = FocusSession.objects.filter(user=request.user)
    if path_id:
        qs = qs.filter(path_id=path_id)
    by_phase = {}
    for row in qs.order_by("-created_at")[:500]:
        entry = by_phase.setdefault(row.phase_idx, {
            "phase_idx": row.phase_idx,
            "phase_title": row.phase_title,
            "seconds": 0,
            "sessions": 0,
        })
        entry["seconds"] += row.seconds
        entry["sessions"] += 1
        if not entry["phase_title"] and row.phase_title:
            entry["phase_title"] = row.phase_title
    return JsonResponse({
        "today_seconds": _today_focus_seconds(qs),
        "total_seconds": sum(qs.values_list("seconds", flat=True)),
        "by_phase": sorted(by_phase.values(), key=lambda e: -e["seconds"])[:12],
    })


def _created_date(meta):
    raw = meta.get("created_at", "")
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc).date()
    except (TypeError, ValueError):
        pass
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _topic_total(path):
    try:
        phases = json.loads(path["content"]).get("phases", [])
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0
    return sum(len(ph.get("topics") or []) for ph in phases)


def _latest_per_lineage(paths):
    latest = {}
    for p in paths:
        meta = p["metadata"]
        lineage = meta.get("lineage") or p["id"]
        try:
            version = int(meta.get("version", 1))
        except (TypeError, ValueError):
            version = 1
        current = latest.get(lineage)
        if current is None or version > current[0]:
            latest[lineage] = (version, p)
    return [p for _, p in latest.values()]


_STATUS_ORDER = {"overdue": 0, "critical": 1, "behind": 2}


@require_GET
def deadline_alerts(request):
    """Compare expected pace to actual checkbox progress for paths with a target_date."""
    denied = _require_user(request)
    if denied:
        return denied
    uid = str(request.user.id)
    paths = [p for p in vector_memory.get_recent_paths(n=500)
             if (p["metadata"].get("owner") or "") == uid]
    paths = _latest_per_lineage(paths)
    today = date.today()
    alerts = []
    checked = 0
    for p in paths:
        meta = p["metadata"]
        if meta.get("format") != "structured":
            continue
        target_raw = (meta.get("target_date") or "").strip()
        if not target_raw:
            continue
        try:
            target = date.fromisoformat(target_raw[:10])
        except ValueError:
            continue
        created = _created_date(meta)
        if created is None:
            continue
        total = _topic_total(p)
        if not total:
            continue
        checked += 1
        done = PathProgress.objects.filter(
            user=request.user, path_id=p["id"], done=True,
        ).count()
        actual = min(100, round(100 * done / total))
        if actual >= 100:
            continue
        total_days = (target - created).days
        if total_days <= 0:
            expected = 100
        else:
            elapsed = (today - created).days
            expected = max(0, min(100, round(100 * elapsed / total_days)))
        days_left = (target - today).days
        behind = expected - actual
        if days_left < 0:
            status = "overdue"
        elif behind >= 25:
            status = "critical"
        elif behind >= 10:
            status = "behind"
        else:
            continue
        alerts.append({
            "path_id": p["id"],
            "goal": meta.get("goal", ""),
            "target_date": target.isoformat(),
            "days_left": days_left,
            "expected_pct": expected,
            "actual_pct": actual,
            "behind": behind,
            "status": status,
        })
    alerts.sort(key=lambda a: (_STATUS_ORDER[a["status"]], -a["behind"]))
    return JsonResponse({"alerts": alerts, "checked": checked})


def _phase_titles(path):
    fmt = path["metadata"].get("format", "markdown")
    if fmt == "structured":
        try:
            phases = json.loads(path["content"]).get("phases", [])
        except (json.JSONDecodeError, ValueError, TypeError):
            phases = []
        return [ph.get("title") or f"Phase {i + 1}" for i, ph in enumerate(phases)]
    return [ph.get("title") or f"Phase {i + 1}" for ph in parse_markdown_phases(path["content"])]


def _phase_stats(user, path_id, phase_idx=None):
    results = TestResult.objects.filter(user=user, path_id=path_id)
    grouped = {}
    for r in results.order_by("created_at"):
        grouped.setdefault(r.phase_idx, []).append(r)
    if phase_idx is not None:
        grouped = {phase_idx: grouped.get(phase_idx, [])}
    return grouped


def _verdict(rows):
    if not rows:
        return None, None
    avg = round(sum(r.percent for r in rows) / len(rows))
    if avg < 60:
        return avg, "too_hard"
    if avg >= 90 and len(rows) >= 2:
        return avg, "too_easy"
    return avg, "ok"


@require_GET
def path_difficulty(request, doc_id):
    """Per-phase test score analysis with too_hard/too_easy verdicts."""
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    user = request.user if request.user.is_authenticated else None
    if user is None:
        return JsonResponse({"error": "Login required to see difficulty analysis"}, status=401)
    grouped = _phase_stats(user, doc_id)
    titles = _phase_titles(path)
    phases = []
    for idx, title in enumerate(titles):
        rows = grouped.get(idx, [])
        avg, verdict = _verdict(rows)
        phases.append({
            "phase_idx": idx,
            "title": title,
            "attempts": len(rows),
            "avg_percent": avg,
            "last_percent": rows[-1].percent if rows else None,
            "verdict": verdict or "no_data",
        })
    return JsonResponse({
        "path_id": doc_id,
        "format": path["metadata"].get("format", "markdown"),
        "phases": phases,
    })


@require_GET
def path_recommendation(request, doc_id):
    """Return an explainable next study action from recorded learner evidence.

    This deliberately uses small, auditable rules instead of claiming mastery from
    sparse data.  A completed checklist item is an engagement signal; a phase-test
    result is the only mastery signal used to trigger remediation.
    """
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err

    from .views import _workspace_data
    from .skill_graph import topic_skill_states

    workspace = _workspace_data(path)
    phases = (workspace or {}).get("phases") or []
    done = set(PathProgress.objects.filter(
        user=request.user, path_id=doc_id, done=True,
    ).values_list("item_key", flat=True))
    results = TestResult.objects.filter(user=request.user, path_id=doc_id).order_by("-created_at")
    latest_scores = {}
    for result in results:
        latest_scores.setdefault(result.phase_idx, result.percent)

    topic_skills = topic_skill_states(request.user, doc_id)

    for phase_idx, phase in enumerate(phases):
        topics = phase.get("topics") or []
        unfinished = [topic for topic in topics if topic.get("key") not in done]
        if unfinished:
            pick = unfinished[0]
            reason = "This is the first unfinished topic, preserving the roadmap's prerequisite order."
            for candidate in unfinished:
                state = topic_skills.get(candidate.get("key", ""))
                if state and state.get("all_validated"):
                    continue
                pick = candidate
                if candidate is not unfinished[0]:
                    reason = (
                        "Earlier topics here map to skills you already validated, "
                        "so the path skips ahead to the first unmastered topic."
                    )
                break
            else:
                reason = (
                    "Every remaining topic maps to skills you already validated — "
                    "move through them quickly as review."
                )
            return JsonResponse({
                "state": "learn",
                "phase_idx": phase_idx,
                "phase_title": phase.get("title", f"Phase {phase_idx + 1}"),
                "topic_key": pick.get("key", ""),
                "topic_title": pick.get("title", "Continue this phase"),
                "reason": reason,
            })

        if topics and phase_idx not in latest_scores:
            return JsonResponse({
                "state": "validate",
                "phase_idx": phase_idx,
                "phase_title": phase.get("title", f"Phase {phase_idx + 1}"),
                "topic_key": "",
                "topic_title": "Check your understanding",
                "reason": "You completed this phase. A short phase check provides evidence before the next dependency.",
            })
        if topics and latest_scores[phase_idx] < 70:
            first_topic = topics[0]
            score = latest_scores[phase_idx]
            return JsonResponse({
                "state": "remediate",
                "phase_idx": phase_idx,
                "phase_title": phase.get("title", f"Phase {phase_idx + 1}"),
                "topic_key": first_topic.get("key", ""),
                "topic_title": first_topic.get("title", "Review this phase"),
                "score": score,
                "reason": f"Your latest phase check was {score}%. Review the foundation, then retake the check.",
            })

        project = MilestoneProject.objects.filter(
            user=request.user, path_id=doc_id, phase_idx=phase_idx,
        ).first()
        if project is not None and project.status != "reviewed":
            return JsonResponse({
                "state": "build",
                "phase_idx": phase_idx,
                "phase_title": phase.get("title", f"Phase {phase_idx + 1}"),
                "topic_key": "",
                "topic_title": project.title,
                "project_status": project.status,
                "reason": "You learned and proved this phase. Ship the capstone project to turn knowledge into evidence.",
            })

    return JsonResponse({
        "state": "complete",
        "phase_idx": max(0, len(phases) - 1),
        "phase_title": "Roadmap complete",
        "topic_key": "",
        "topic_title": "Celebrate and choose your next goal",
        "reason": "Every topic has been completed and each phase has learning evidence.",
    })


RETUNE_SYSTEM = """You are an expert curriculum designer rewriting ONE phase of a structured learning roadmap to adjust its difficulty.

Return ONLY a valid JSON object (no markdown fences, no commentary) for the single phase with exactly this schema:
{{
  "title": "phase name",
  "description": "what this phase covers",
  "estimated_weeks": <number>,
  "topics": [
    {{
      "title": "topic name",
      "details": "1-2 sentence explanation",
      "resources": [
        {{"name": "resource name", "type": "course|book|video|article|tool|docs", "note": "one short sentence"}}
      ]
    }}
  ]
}}

Direction: {direction}
- "easier": break concepts into smaller steps, add scaffolding and gentler prerequisites, recommend more beginner-friendly resources, keep the same subject.
- "harder": go deeper — add optimization, edge cases, system design or open-ended challenge projects, assume stronger prerequisites.

Keep the phase focused on the same goal and phase position in the roadmap. 3 to 6 topics, 2 to 4 real resources per topic. Output ONLY the JSON object."""


def _retune_phase_llm(goal, phase, direction, score_note):
    chain = (ChatPromptTemplate.from_messages([
        ("system", RETUNE_SYSTEM),
        ("human", """Learning goal: {goal}

Direction: {direction}
Average test score on this phase: {score}

Current phase JSON:
{phase_json}"""),
    ]) | _get_llm() | StrOutputParser())
    raw = chain.invoke({
        "goal": goal or "this learning path",
        "direction": direction,
        "score": score_note,
        "phase_json": json.dumps(phase, indent=1)[:6000],
    })
    return _parse_json(raw)


@csrf_exempt
@require_POST
def path_retune(request, doc_id):
    """Rewrite one phase easier/harder and save the path as a new version."""
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    data = _json_body(request)
    meta = path["metadata"]
    if meta.get("format") != "structured":
        return JsonResponse(
            {"error": "Only interactive roadmaps support phase retuning. Regenerate the path instead."},
            status=400,
        )
    try:
        phase_idx = int(data.get("phase_idx", -1))
    except (TypeError, ValueError):
        phase_idx = -1
    try:
        phases = json.loads(path["content"]).get("phases", [])
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"error": "Invalid path data"}, status=400)
    if phase_idx < 0 or phase_idx >= len(phases):
        return JsonResponse({"error": "Phase not found"}, status=404)

    direction = (data.get("direction") or "").strip().lower()
    if direction not in ("easier", "harder"):
        rows = _phase_stats(request.user, doc_id, phase_idx).get(phase_idx, [])
        avg, verdict = _verdict(rows)
        if verdict == "too_hard":
            direction = "easier"
        elif verdict == "too_easy":
            direction = "harder"
        elif verdict is None:
            return JsonResponse(
                {"error": "No test data for this phase — pass direction (easier or harder)."},
                status=400,
            )
        else:
            return JsonResponse(
                {"error": "Phase looks balanced — pass direction (easier or harder) to retune."},
                status=400,
            )

    rows = _phase_stats(request.user, doc_id, phase_idx).get(phase_idx, [])
    avg, _ = _verdict(rows)
    score_note = f"{avg}% across {len(rows)} attempt(s)" if rows else "no attempts yet"

    goal = meta.get("goal", "")
    if not goal:
        return JsonResponse({"error": "Original goal is missing; retune is unavailable."}, status=400)

    try:
        new_phase = _retune_phase_llm(goal, phases[phase_idx], direction, score_note)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    if not isinstance(new_phase, dict) or not new_phase.get("title") or not isinstance(new_phase.get("topics"), list):
        return JsonResponse({"error": "Model returned an invalid phase; nothing was saved."}, status=502)

    phases[phase_idx] = new_phase
    try:
        structured = json.loads(path["content"])
    except (json.JSONDecodeError, ValueError, TypeError):
        structured = {"phases": []}
    structured["phases"] = phases
    doc = json.dumps(structured)

    params = {
        "goal": goal,
        "current_level": meta.get("current_level", "beginner"),
        "hours_per_day": meta.get("hours_per_day", 2),
        "format_preference": meta.get("format_preference", "courses and hands-on projects"),
        "months": meta.get("months", 6),
        "target_date": meta.get("target_date", ""),
    }
    new_meta = _version_meta(request, path, params, "structured")
    new_meta["retuned_phase"] = str(phase_idx)
    try:
        new_id = vector_memory.save_path(goal, doc, meta=new_meta)
        copied = _copy_progress(doc_id, new_id, request.user)
        record_activity(request.user, "path")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        "id": new_id,
        "version": int(new_meta["version"]),
        "lineage": new_meta["lineage"],
        "copied_progress": copied,
        "phase_idx": phase_idx,
        "direction": direction,
    })

import sys
import os
import json
import re
import time
import uuid
import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


def _cache_get(key, max_age_hours=168):
    path = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        age = time.time() - entry.get("ts", 0)
        if age < max_age_hours * 3600:
            return entry.get("data")
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def _cache_set(key, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        path = os.path.join(CACHE_DIR, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except OSError:
        pass

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from django.contrib.auth.models import User

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.react_agent import run_agent
from chains.path_generator import (
    generate_learning_path,
    generate_learning_path_structured,
    generate_phase_quiz,
    generate_placement_quiz,
    parse_markdown_phases,
    phase_from_markdown_body,
    stream_learning_path,
)
from memory.vector_store import vector_memory
from config import GEMINI_API_KEY, GEMINI_MODEL
from .models import Feedback, PathProgress, ShareLink, TestResult
from .progress_stats import record_activity
from .badges import evaluate as evaluate_badges


def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return {}


def _get_llm():
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.3)


def _user_id(request):
    return str(request.user.id) if request.user.is_authenticated else None


def _can_access(request, meta):
    owner = (meta or {}).get("owner", "")
    uid = _user_id(request)
    if not owner:
        return True
    return uid is not None and owner == uid


def _path_or_none(doc_id):
    return vector_memory.get_path(doc_id)


DOMAINS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a learning advisor. Return a JSON array of learning domains. Each object must have: name (snake_case string), label (display name), description (one sentence). Return ONLY valid JSON array, no markdown."),
    ("human", "List the main learning domains/career paths available in tech education."),
])

DOMAIN_TOPICS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a learning advisor. Return a JSON object with key 'topics' containing an array of topic objects. Each topic has: name (string), description (one sentence). Return ONLY valid JSON, no markdown."),
    ("human", "List the key topics and subtopics someone needs to learn for {domain}."),
])

RESOURCE_SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a learning resource curator. Return a JSON array of learning resource topics. Each object must have: topic_name (string), domain (snake_case string), category (snake_case string), difficulty (one of: beginner, intermediate, advanced), estimated_hours (number), description (one sentence). Return ONLY a valid JSON array, no markdown."),
    ("human", "Search query: {query}\nDomain filter: {domain}\nDifficulty filter: {difficulty}\n\nList up to 12 high-quality learning resources/topics matching these filters. Use real, well-known topics and free learning resources."),
])

CHAT_SYSTEM = """You are a friendly learning coach chatbot. The user is asking questions about their saved learning path below. Answer concisely and helpfully, referring to the path content when relevant. If asked something unrelated to learning/careers, steer them back to their roadmap.

--- LEARNING PATH START ---
{path_content}
--- LEARNING PATH END ---"""


@csrf_exempt
@require_POST
def agent_generate(request):
    data = _json_body(request)
    goal = data.get("goal", "").strip()
    if not goal:
        return JsonResponse({"error": "Goal is required"}, status=400)
    try:
        result = run_agent(goal)
        return JsonResponse({"output": result["output"], "steps": result["steps"]})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _parse_gen_params(data):
    try:
        months = int(data.get("months", 6))
    except (TypeError, ValueError):
        months = 6
    return {
        "goal": (data.get("goal") or "").strip(),
        "current_level": data.get("current_level", "beginner"),
        "hours_per_day": data.get("hours_per_day", 2),
        "format_preference": data.get("format_preference", "courses and hands-on projects"),
        "months": max(1, months),
        "target_date": (data.get("target_date") or "").strip(),
    }


def _base_meta(request, params, fmt):
    meta = {
        "source": "quick",
        "current_level": params["current_level"],
        "hours_per_day": str(params["hours_per_day"]),
        "months": str(params["months"]),
        "format": fmt,
        "format_preference": params["format_preference"],
        "version": "1",
    }
    if params["target_date"]:
        meta["target_date"] = params["target_date"]
    uid = _user_id(request)
    if uid:
        meta["owner"] = uid
    return meta


def _version_meta(request, parent, params, fmt):
    """Metadata for a regenerated path: keeps the lineage, bumps the version."""
    pmeta = parent["metadata"]
    meta = _base_meta(request, params, fmt)
    meta["source"] = pmeta.get("source", "quick")
    meta["lineage"] = pmeta.get("lineage") or parent["id"]
    try:
        meta["version"] = str(int(pmeta.get("version", 1)) + 1)
    except (TypeError, ValueError):
        meta["version"] = "2"
    return meta


def _effective_lineage(path):
    meta = path["metadata"]
    return meta.get("lineage") or path["id"]


def _copy_progress(from_path_id, to_path_id, user):
    if user is None or not user.is_authenticated:
        return 0
    rows = PathProgress.objects.filter(user=user, path_id=from_path_id)
    copied = 0
    for row in rows:
        _, created = PathProgress.objects.update_or_create(
            user=user, path_id=to_path_id, item_key=row.item_key,
            defaults={"done": row.done},
        )
        copied += 1 if created else 0
    return copied


@csrf_exempt
@require_POST
def path_generate(request):
    data = _json_body(request)
    params = _parse_gen_params(data)
    if not params["goal"]:
        return JsonResponse({"error": "Goal is required"}, status=400)
    try:
        output = generate_learning_path(**params)
        doc_id = vector_memory.save_path(params["goal"], output, meta=_base_meta(request, params, "markdown"))
        record_activity(request.user, "path")
        return JsonResponse({"output": output, "id": doc_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def path_structured(request):
    data = _json_body(request)
    params = _parse_gen_params(data)
    if not params["goal"]:
        return JsonResponse({"error": "Goal is required"}, status=400)
    try:
        structured = generate_learning_path_structured(**params)
        doc = json.dumps(structured)
        doc_id = vector_memory.save_path(params["goal"], doc, meta=_base_meta(request, params, "structured"))
        record_activity(request.user, "path")
        return JsonResponse({"output": structured, "id": doc_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def path_stream(request):
    data = _json_body(request)
    params = _parse_gen_params(data)
    if not params["goal"]:
        return JsonResponse({"error": "Goal is required"}, status=400)

    def event_stream():
        try:
            for text in stream_learning_path(**params):
                yield f"data: {json.dumps({'chunk': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


@csrf_exempt
@require_POST
def path_stream_save(request):
    data = _json_body(request)
    params = _parse_gen_params(data)
    output = data.get("output", "").strip()
    if not params["goal"] or not output:
        return JsonResponse({"error": "goal and output are required"}, status=400)
    try:
        doc_id = vector_memory.save_path(params["goal"], output, meta=_base_meta(request, params, "markdown"))
        record_activity(request.user, "path")
        return JsonResponse({"id": doc_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def paths_history(request):
    try:
        paths = vector_memory.get_recent_paths(n=50)
        uid = _user_id(request)
        items = []
        for p in paths:
            meta = p["metadata"]
            owner = meta.get("owner", "")
            if uid is None:
                if owner:
                    continue
            elif owner and owner != uid:
                continue
            items.append({
                "id": p["id"],
                "goal": meta.get("goal", ""),
                "created_at": meta.get("created_at", ""),
                "source": meta.get("source", "agent"),
                "current_level": meta.get("current_level", ""),
                "hours_per_day": meta.get("hours_per_day", ""),
                "months": meta.get("months", ""),
                "format": meta.get("format", "markdown"),
                "target_date": meta.get("target_date", ""),
                "lineage": meta.get("lineage") or p["id"],
                "version": int(meta.get("version", 1) or 1),
                "content": p["content"],
            })
        return JsonResponse({"paths": items})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _structured_phases(path):
    try:
        return json.loads(path["content"]).get("phases", [])
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


@require_GET
def paths_phases(request, doc_id):
    """List phases for a path. Works for both structured and plain-markdown roadmaps."""
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return JsonResponse({"error": "Not allowed"}, status=403)

    fmt = path["metadata"].get("format", "markdown")
    if fmt == "structured":
        titles = [p.get("title", f"Phase {i + 1}") for i, p in enumerate(_structured_phases(path))]
    else:
        titles = [p.get("title", f"Phase {i + 1}") for i, p in enumerate(parse_markdown_phases(path["content"]))]
    return JsonResponse({"phases": titles, "format": fmt})


_MD_TOPIC_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_MD_BULLET_RE = re.compile(r"^\s*[-*•]\s+(.*)$")


def _structured_workspace(path) -> dict | None:
    try:
        structured = json.loads(path["content"])
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    phases = []
    for pi, ph in enumerate(structured.get("phases") or []):
        if not isinstance(ph, dict):
            continue
        topics = []
        for ti, t in enumerate(ph.get("topics") or []):
            if not isinstance(t, dict):
                continue
            topics.append({
                "index": ti,
                "key": f"t:{pi}:{ti}",
                "title": t.get("title", ""),
                "details": t.get("details", ""),
                "resources": [
                    {
                        "name": r.get("name", ""),
                        "type": r.get("type", ""),
                        "note": r.get("note", ""),
                    }
                    for r in (t.get("resources") or []) if isinstance(r, dict)
                ],
            })
        phases.append({
            "index": pi,
            "title": ph.get("title", f"Phase {pi + 1}"),
            "description": ph.get("description", ""),
            "estimated_weeks": ph.get("estimated_weeks"),
            "topics": topics,
        })
    return {
        "title": structured.get("title", ""),
        "summary": structured.get("summary", ""),
        "total_weeks": structured.get("total_weeks"),
        "phases": phases,
    }


def _markdown_workspace(path) -> dict:
    phases = []
    for pi, ph in enumerate(parse_markdown_phases(path["content"])):
        topics = []
        ti = 0
        for line in ph.get("raw", "").splitlines():
            m = _MD_BULLET_RE.match(line)
            if not m:
                continue
            text = m.group(1).strip()
            if not text or text.startswith("|") or text.startswith("#"):
                continue
            links = _MD_TOPIC_LINK_RE.findall(text)
            cleaned = _MD_TOPIC_LINK_RE.sub("", text).strip()
            cleaned = cleaned.strip("*_`").strip().rstrip(":·-–—").strip()
            title = cleaned or (links[0][0] if links else text[:140])
            topics.append({
                "index": ti,
                "key": f"t:{pi}:{ti}",
                "title": title,
                "details": "",
                "resources": [
                    {"name": name, "type": "link", "note": url}
                    for name, url in links
                ],
            })
            ti += 1
        if not topics:
            summary = phase_from_markdown_body(ph)
            topics.append({
                "index": 0,
                "key": f"t:{pi}:0",
                "title": "Review this phase's material",
                "details": (summary.get("description") or ph.get("title", ""))[:300],
                "resources": [],
            })
        phases.append({
            "index": pi,
            "title": ph.get("title", f"Phase {pi + 1}"),
            "description": "",
            "estimated_weeks": None,
            "topics": topics,
        })
    return {"title": "", "summary": "", "total_weeks": None, "phases": phases}


def _workspace_data(path) -> dict | None:
    if path["metadata"].get("format") == "structured":
        return _structured_workspace(path)
    return _markdown_workspace(path)


@require_GET
def paths_workspace(request, doc_id):
    """Full interactive workspace payload: phases, topics, resources and done keys."""
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return JsonResponse({"error": "Not allowed"}, status=403)
    data = _workspace_data(path)
    if data is None:
        return JsonResponse({"error": "Invalid path data"}, status=400)
    done = []
    if request.user.is_authenticated:
        done = list(PathProgress.objects.filter(
            user=request.user, path_id=doc_id, done=True,
        ).values_list("item_key", flat=True))
    meta = path["metadata"]
    return JsonResponse({
        "id": doc_id,
        "goal": meta.get("goal", ""),
        "format": meta.get("format", "markdown"),
        "hours_per_day": meta.get("hours_per_day", ""),
        "target_date": meta.get("target_date", ""),
        "version": int(meta.get("version", 1) or 1),
        **data,
        "done": done,
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def paths_delete(request, doc_id):
    try:
        path = _path_or_none(doc_id)
        if path is None:
            return JsonResponse({"error": "Path not found"}, status=404)
        if not _can_access(request, path["metadata"]):
            return JsonResponse({"error": "Not allowed"}, status=403)
        vector_memory.delete_path(doc_id)
        ShareLink.objects.filter(path_id=doc_id).delete()
        return JsonResponse({"deleted": True, "id": doc_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def paths_chat(request, doc_id):
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return JsonResponse({"error": "Not allowed"}, status=403)
    data = _json_body(request)
    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)
    history = data.get("history") or []
    try:
        content = path["content"]
        if path["metadata"].get("format") == "structured":
            content = json.dumps(json.loads(content), indent=1)
        messages = [("system", CHAT_SYSTEM.format(path_content=content[:8000]))]
        for h in history[-10:]:
            role = "assistant" if h.get("role") == "assistant" else "human"
            messages.append((role, str(h.get("content", ""))))
        messages.append(("human", message))
        chain = ChatPromptTemplate.from_messages(messages) | _get_llm() | StrOutputParser()
        reply = chain.invoke({})
        return JsonResponse({"reply": reply})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def paths_progress(request, doc_id):
    if not request.user.is_authenticated:
        return JsonResponse({"done": []})
    done = list(PathProgress.objects.filter(
        user=request.user, path_id=doc_id, done=True,
    ).values_list("item_key", flat=True))
    return JsonResponse({"done": done})


@csrf_exempt
@require_POST
def paths_progress_save(request, doc_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required to sync progress"}, status=401)
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return JsonResponse({"error": "Not allowed"}, status=403)
    data = _json_body(request)
    item_key = (data.get("item_key") or "").strip()
    done = bool(data.get("done", True))
    if not item_key:
        return JsonResponse({"error": "item_key is required"}, status=400)
    PathProgress.objects.update_or_create(
        user=request.user, path_id=doc_id, item_key=item_key,
        defaults={"done": done},
    )
    if done:
        record_activity(request.user, "topic")
    total = PathProgress.objects.filter(user=request.user, path_id=doc_id, done=True).count()
    return JsonResponse({"ok": True, "done_count": total})


@csrf_exempt
@require_POST
def paths_feedback(request, doc_id):
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    data = _json_body(request)
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "value must be 1 or -1"}, status=400)
    if value not in (1, -1):
        return JsonResponse({"error": "value must be 1 or -1"}, status=400)
    try:
        Feedback.objects.update_or_create(
            path_id=doc_id, user=request.user if request.user.is_authenticated else None,
            defaults={"value": value},
        )
    except Exception:
        Feedback.objects.filter(
            path_id=doc_id, user=request.user if request.user.is_authenticated else None,
        ).delete()
        Feedback.objects.create(
            path_id=doc_id,
            user=request.user if request.user.is_authenticated else None,
            value=value,
        )
    up = Feedback.objects.filter(path_id=doc_id, value=1).count()
    down = Feedback.objects.filter(path_id=doc_id, value=-1).count()
    return JsonResponse({"up": up, "down": down})


@require_GET
def paths_ics(request, doc_id):
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    meta = path["metadata"]
    goal = meta.get("goal", "Learning Path")
    try:
        created = datetime.fromtimestamp(float(meta.get("created_at", 0)), tz=timezone.utc)
    except (TypeError, ValueError):
        created = datetime.now(tz=timezone.utc)

    events = []
    if meta.get("format") == "structured":
        try:
            structured = json.loads(path["content"])
            cursor = created.date()
            for i, phase in enumerate(structured.get("phases", [])):
                weeks = int(phase.get("estimated_weeks", 4) or 4)
                start = cursor
                end = start + timedelta(weeks=weeks)
                events.append({
                    "summary": f"Phase {i + 1}: {phase.get('title', 'Phase')}",
                    "description": phase.get("description", goal),
                    "start": start,
                    "end": end,
                })
                cursor = end
        except (json.JSONDecodeError, ValueError, TypeError):
            events = []
    if not events:
        months = int(meta.get("months", 6) or 6)
        events.append({
            "summary": f"Learning Path: {goal}",
            "description": f"Roadmap to achieve: {goal}",
            "start": created.date(),
            "end": created.date() + timedelta(days=30 * max(1, months)),
        })

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LearnPath//EN"]
    for ev in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}",
            f"DTSTAMP:{created.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{ev['start'].strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{ev['end'].strftime('%Y%m%d')}",
            f"SUMMARY:{ev['summary']}",
            f"DESCRIPTION:{ev['description']}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines)
    resp = StreamingHttpResponse(iter([body]), content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{doc_id}.ics"'
    return resp


@csrf_exempt
@require_POST
def placement_start(request):
    data = _json_body(request)
    goal = (data.get("goal") or "").strip()
    if not goal:
        return JsonResponse({"error": "Goal is required"}, status=400)
    try:
        quiz = generate_placement_quiz(goal)
        questions = quiz.get("questions", [])[:5]
        quiz_id = uuid.uuid4().hex
        session_quiz = []
        safe_questions = []
        for q in questions:
            session_quiz.append({
                "id": q.get("id"),
                "answer_index": int(q.get("answer_index", 0)),
            })
            safe_questions.append({
                "id": q.get("id"),
                "question": q.get("question", ""),
                "options": q.get("options", []),
            })
        request.session[f"placement_{quiz_id}"] = {"goal": goal, "questions": session_quiz}
        return JsonResponse({"quiz_id": quiz_id, "questions": safe_questions})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def placement_submit(request):
    data = _json_body(request)
    quiz_id = (data.get("quiz_id") or "").strip()
    stored = request.session.get(f"placement_{quiz_id}")
    if not stored:
        return JsonResponse({"error": "Quiz not found or expired"}, status=404)
    answers = data.get("answers") or {}
    correct = 0
    total = len(stored["questions"])
    for q in stored["questions"]:
        try:
            if int(answers.get(q["id"], -1)) == q["answer_index"]:
                correct += 1
        except (TypeError, ValueError):
            pass
    pct = int(round(100 * correct / total)) if total else 0
    if pct >= 80:
        level = "advanced"
    elif pct >= 50:
        level = "intermediate"
    else:
        level = "beginner"
    del request.session[f"placement_{quiz_id}"]
    return JsonResponse({"score": correct, "total": total, "percent": pct, "suggested_level": level})


@csrf_exempt
@require_POST
def phase_test_start(request, doc_id, phase_idx):
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return JsonResponse({"error": "Not allowed"}, status=403)

    is_structured = path["metadata"].get("format") == "structured"
    if is_structured:
        try:
            structured = json.loads(path["content"])
            phases = structured.get("phases", [])
            if phase_idx < 0 or phase_idx >= len(phases):
                return JsonResponse({"error": "Phase not found"}, status=404)
            phase = phases[phase_idx]
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({"error": "Invalid path data"}, status=400)
    else:
        md_phases = parse_markdown_phases(path["content"])
        if not md_phases:
            return JsonResponse({"error": "No phases could be detected in this roadmap. Regenerate it as an interactive checklist to take phase tests."}, status=400)
        if phase_idx < 0 or phase_idx >= len(md_phases):
            return JsonResponse({"error": "Phase not found"}, status=404)
        phase = phase_from_markdown_body(md_phases[phase_idx])

    data = _json_body(request)
    try:
        count = int(data.get("count", 5))
    except (TypeError, ValueError):
        count = 5
    avoid = data.get("avoid") or []
    if not isinstance(avoid, list):
        avoid = []

    try:
        quiz = generate_phase_quiz(
            goal=path["metadata"].get("goal", "learning"),
            phase=phase,
            count=count,
            avoid=avoid,
        )
        questions = quiz.get("questions", [])[:max(1, min(10, count))]
        quiz_id = uuid.uuid4().hex
        session_quiz = []
        safe_questions = []
        for q in questions:
            session_quiz.append({
                "id": q.get("id"),
                "answer_index": int(q.get("answer_index", 0)),
                "question": q.get("question", ""),
                "options": q.get("options", []),
            })
            safe_questions.append({
                "id": q.get("id"),
                "question": q.get("question", ""),
                "options": q.get("options", []),
            })
        request.session[f"test_{quiz_id}"] = {
            "path_id": doc_id,
            "phase_idx": phase_idx,
            "phase_title": phase.get("title", ""),
            "questions": session_quiz,
        }
        return JsonResponse({"quiz_id": quiz_id, "questions": safe_questions, "phase_title": phase.get("title", "")})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def phase_test_submit(request):
    data = _json_body(request)
    quiz_id = (data.get("quiz_id") or "").strip()
    stored = request.session.get(f"test_{quiz_id}")
    if not stored:
        return JsonResponse({"error": "Test not found or expired"}, status=404)
    answers = data.get("answers") or {}
    correct = 0
    results = []
    for q in stored["questions"]:
        try:
            user_index = int(answers.get(q["id"], -1))
        except (TypeError, ValueError):
            user_index = -1
        is_correct = user_index == q["answer_index"]
        if is_correct:
            correct += 1
        results.append({
            "id": q["id"],
            "correct_index": q["answer_index"],
            "user_index": user_index,
            "correct": is_correct,
        })
    total = len(stored["questions"])
    pct = int(round(100 * correct / total)) if total else 0
    del request.session[f"test_{quiz_id}"]

    remediation = None
    missed = [q for q, r in zip(stored["questions"], results) if not r["correct"] and q.get("question")]
    if missed:
        remed_id = uuid.uuid4().hex
        request.session[f"test_{remed_id}"] = {
            "path_id": stored.get("path_id", ""),
            "phase_idx": stored.get("phase_idx", 0),
            "phase_title": stored.get("phase_title", ""),
            "questions": missed,
        }
        remediation = {
            "quiz_id": remed_id,
            "phase_title": stored.get("phase_title", ""),
            "count": len(missed),
            "questions": [
                {"id": q["id"], "question": q["question"], "options": q.get("options", [])}
                for q in missed
            ],
        }

    if request.user.is_authenticated:
        TestResult.objects.create(
            user=request.user,
            path_id=stored.get("path_id", ""),
            phase_idx=int(stored.get("phase_idx", 0) or 0),
            phase_title=stored.get("phase_title", ""),
            score=correct,
            total=total,
            percent=pct,
        )
    record_activity(request.user, "test")

    return JsonResponse({
        "score": correct,
        "total": total,
        "percent": pct,
        "results": results,
        "remediation": remediation,
        "badges": evaluate_badges(request.user) if request.user.is_authenticated else [],
    })


@require_GET
def stats(request):
    try:
        recent = vector_memory.get_recent_paths(n=1000)
        now = datetime.now(tz=timezone.utc)
        by_day = Counter()
        by_source = Counter()
        goals = Counter()
        for p in recent:
            meta = p["metadata"]
            by_source[meta.get("source", "agent")] += 1
            goal = (meta.get("goal") or "").strip().lower()
            if goal:
                goals[goal] += 1
            try:
                ts = float(meta.get("created_at", 0))
                d = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            except (TypeError, ValueError):
                continue
            by_day[d.isoformat()] += 1
        days = [(now - timedelta(days=i)).date().isoformat() for i in range(13, -1, -1)]
        by_day_list = [{"date": d, "count": by_day.get(d, 0)} for d in days]
        return JsonResponse({
            "total_paths": len(recent),
            "by_source": dict(by_source),
            "by_day": by_day_list,
            "top_goals": [{"goal": g, "count": c} for g, c in goals.most_common(8)],
            "feedback": {
                "up": Feedback.objects.filter(value=1).count(),
                "down": Feedback.objects.filter(value=-1).count(),
            },
            "total_users": User.objects.count(),
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_domains(request):
    cached = _cache_get("domains")
    if cached is not None:
        return JsonResponse({"domains": cached, "cached": True})
    try:
        chain = DOMAINS_PROMPT | _get_llm() | StrOutputParser()
        raw = chain.invoke({})
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        domains = json.loads(raw)
        _cache_set("domains", domains)
        return JsonResponse({"domains": domains})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_domain_topics(request, domain):
    cache_key = f"topics_{domain}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return JsonResponse({"domain": domain, "topics": cached, "cached": True})
    try:
        chain = DOMAIN_TOPICS_PROMPT | _get_llm() | StrOutputParser()
        raw = chain.invoke({"domain": domain.replace("-", " ").replace("_", " ")})
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        topics = data.get("topics", [])
        _cache_set(cache_key, topics)
        return JsonResponse({"domain": domain, "topics": topics})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _strip_fences(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return raw


@require_GET
def resource_search(request):
    query = request.GET.get("query", "").strip()
    domain = request.GET.get("domain", "").strip()
    difficulty = request.GET.get("difficulty", "any").strip()
    cache_key = "res_" + hashlib.md5(f"{query}|{domain}|{difficulty}".encode()).hexdigest()
    cached = _cache_get(cache_key, max_age_hours=72)
    if cached is not None:
        return JsonResponse({"results": cached, "cached": True})
    try:
        chain = RESOURCE_SEARCH_PROMPT | _get_llm() | StrOutputParser()
        raw = _strip_fences(chain.invoke({
            "query": query or "popular tech learning topics",
            "domain": domain or "any",
            "difficulty": difficulty,
        }))
        items = json.loads(raw)
        if not isinstance(items, list):
            raise ValueError("Expected a JSON array of resources")
        results = [
            {"metadata": it} for it in items
            if isinstance(it, dict) and it.get("topic_name")
        ]
        _cache_set(cache_key, results)
        return JsonResponse({"results": results})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

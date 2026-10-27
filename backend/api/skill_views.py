"""Skill graph endpoints: extraction from a roadmap and the mastery matrix."""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from chains.path_generator import generate_skill_graph
from .skill_graph import apply_skill_graph, path_skill_matrix
from .study_views import _load_path, _require_user
from .views import _json_body, _workspace_data


def _flat_topics(ws) -> list:
    topics = []
    for phase in (ws or {}).get("phases") or []:
        for t in phase.get("topics") or []:
            if not t.get("title"):
                continue
            topics.append({
                "key": t.get("key", ""),
                "title": t.get("title", ""),
                "details": t.get("details", ""),
            })
    return topics


@csrf_exempt
@require_POST
def skills_extract(request, doc_id):
    """Extract a skill graph (skills, prerequisites, topic mappings) for this roadmap."""
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err

    ws = _workspace_data(path)
    topics = _flat_topics(ws)
    if not topics:
        return JsonResponse({"error": "No topics found in this path."}, status=400)

    try:
        graph = generate_skill_graph(goal=path["metadata"].get("goal", "learning"), topics=topics)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    if not isinstance(graph, dict) or not graph.get("skills"):
        return JsonResponse({"error": "The model returned an invalid skill graph; nothing was saved."}, status=502)

    topic_titles = {t["key"]: t["title"] for t in topics if t.get("key")}
    result = apply_skill_graph(request.user, doc_id, graph, topic_titles=topic_titles)
    matrix = path_skill_matrix(request.user, doc_id)
    return JsonResponse({
        "extracted": len(result["skills"]),
        "edges": len(result["edges"]),
        "topics_mapped": result["topics_mapped"],
        "matrix": matrix,
    })


@require_GET
def skills_matrix(request, doc_id):
    """Mastery matrix for one path: each skill's state and prerequisite edges."""
    denied = _require_user(request)
    if denied:
        return denied
    path, err = _load_path(request, doc_id)
    if err:
        return err
    matrix = path_skill_matrix(request.user, doc_id)
    matrix["goal"] = path["metadata"].get("goal", "")
    matrix["path_id"] = doc_id
    return JsonResponse(matrix)

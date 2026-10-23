"""Badge catalogue and evaluation."""
import json

from .models import Badge, PathProgress, StudyActivity, TestResult
from .progress_stats import streaks
from memory.vector_store import vector_memory

BADGES = [
    {"key": "first-path", "name": "First Steps", "description": "Generated your first learning path.", "icon": "Flag"},
    {"key": "path-collector", "name": "Path Collector", "description": "Generated 5 learning paths.", "icon": "Layers"},
    {"key": "phase-1-complete", "name": "Phase 1 Complete", "description": "Finished every topic in Phase 1 of a path.", "icon": "Trophy"},
    {"key": "perfect-test", "name": "Perfect Score", "description": "Scored 100% on a phase test.", "icon": "Target"},
    {"key": "streak-7", "name": "7-Day Streak", "description": "Studied 7 days in a row.", "icon": "Flame"},
    {"key": "streak-30", "name": "30-Day Streak", "description": "Studied 30 days in a row.", "icon": "Flame"},
    {"key": "quiz-master", "name": "Quiz Master", "description": "Completed 5 phase tests.", "icon": "ClipboardCheck"},
    {"key": "review-100", "name": "Card Shark", "description": "Reviewed 100 flashcards.", "icon": "Layers"},
]


def _phase_one_complete(user):
    rows = PathProgress.objects.filter(user=user, done=True, item_key__startswith="t:0:")
    for path_id in {r.path_id for r in rows}:
        done = set(
            PathProgress.objects.filter(
                user=user, path_id=path_id, done=True,
            ).values_list("item_key", flat=True)
        )
        phase_zero = {k for k in done if k.startswith("t:0:")}
        if not phase_zero:
            continue
        path = vector_memory.get_path(path_id)
        if path is None:
            continue
        total = _phase_topic_count(path)
        if total and len(phase_zero) >= total:
            return True
    return False


def _phase_topic_count(path):
    try:
        phases = json.loads(path["content"]).get("phases", [])
        if phases:
            return len(phases[0].get("topics") or [])
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0
    return 0


def _owned_paths(user):
    paths = vector_memory.get_recent_paths(n=500)
    return [p for p in paths if (p["metadata"].get("owner") or "") == str(user.id)]


def evaluate(user):
    """Return the earned status of every badge for this user."""
    if user is None or not user.is_authenticated:
        return []

    path_count = len(_owned_paths(user))
    review_count = _review_total(user)
    current_streak = streaks(user)["current"]

    earned_now = {
        "first-path": path_count >= 1,
        "path-collector": path_count >= 5,
        "phase-1-complete": _phase_one_complete(user),
        "perfect-test": TestResult.objects.filter(user=user, percent=100).exists(),
        "streak-7": current_streak >= 7,
        "streak-30": current_streak >= 30,
        "quiz-master": TestResult.objects.filter(user=user).count() >= 5,
        "review-100": review_count >= 100,
    }

    existing = {b.key: b.earned_at for b in Badge.objects.filter(user=user)}
    out = []
    for defn in BADGES:
        key = defn["key"]
        if earned_now.get(key) and key not in existing:
            row = Badge.objects.create(user=user, key=key)
            existing[key] = row.earned_at
        is_earned = bool(earned_now.get(key)) or key in existing
        entry = dict(defn)
        entry["earned"] = is_earned
        entry["earned_at"] = _iso(existing.get(key)) if is_earned else None
        out.append(entry)
    return out


def _review_total(user):
    return sum(r.count for r in StudyActivity.objects.filter(user=user, kind="review"))


def _iso(dt):
    return dt.isoformat() if dt else None

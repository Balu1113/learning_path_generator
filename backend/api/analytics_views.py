import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from .models import (
    LearningAnalytics, FocusSession, TestResult, PathProgress
)
from .views import _path_or_none, _can_access
from .schedule_builder import path_phases


def _load_path(request, doc_id):
    path = _path_or_none(doc_id)
    if path is None:
        return None, JsonResponse({"error": "Path not found"}, status=404)
    if not _can_access(request, path["metadata"]):
        return None, JsonResponse({"error": "Not allowed"}, status=403)
    return path, None


def _topics_total(path):
    """Count topics in a structured or markdown path (phases excluded)."""
    total = 0
    for phase in path_phases(path):
        total += sum(1 for t in (phase.get("topics") or []) if t.get("title"))
    return total


def _path_activity(user, path_id):
    """Distinct active days and last-activity timestamp for a user on a path."""
    dates = set()
    last = None
    for model, field in (
        (PathProgress, "updated_at"),
        (TestResult, "created_at"),
        (FocusSession, "created_at"),
    ):
        for value in model.objects.filter(user=user, path_id=path_id).values_list(field, flat=True):
            if value is None:
                continue
            local = timezone.localtime(value) if timezone.is_aware(value) else value
            dates.add(local.date())
            if last is None or value > last:
                last = value
    return len(dates), last


def _upsert_analytics(user, path_id, fields):
    """Refresh the cached LearningAnalytics row with freshly computed values."""
    obj, _ = LearningAnalytics.objects.get_or_create(user=user, path_id=path_id)
    for key, value in fields.items():
        setattr(obj, key, value)
    obj.save()
    return obj


@require_GET
def analytics_dashboard(request, doc_id):
    """Get comprehensive learning analytics for a path."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    path, error = _load_path(request, doc_id)
    if error:
        return error

    total_time_seconds = FocusSession.objects.filter(
        user=request.user, path_id=doc_id
    ).aggregate(total=Sum('seconds'))['total'] or 0

    topics_completed = PathProgress.objects.filter(
        user=request.user, path_id=doc_id, done=True
    ).count()

    topics_total = _topics_total(path)
    if topics_total == 0:
        remaining = PathProgress.objects.filter(
            user=request.user, path_id=doc_id, done=False
        ).count()
        topics_total = topics_completed + remaining

    test_results = TestResult.objects.filter(user=request.user, path_id=doc_id)
    avg_score = test_results.aggregate(avg=Avg('percent'))['avg'] or 0

    weak_areas = _identify_weak_areas(request.user, doc_id, path)
    completion_rate = (topics_completed / max(1, topics_total)) * 100
    days_active, last_activity = _path_activity(request.user, doc_id)

    predicted_days = _predict_completion(topics_completed, topics_total, days_active)

    week_ago = timezone.now() - timedelta(days=7)
    topics_this_week = PathProgress.objects.filter(
        user=request.user, path_id=doc_id, done=True, updated_at__gte=week_ago
    ).count()

    _upsert_analytics(request.user, doc_id, {
        "total_time_minutes": total_time_seconds // 60,
        "topics_completed": topics_completed,
        "topics_total": topics_total,
        "velocity_topics_per_week": topics_this_week,
        "predicted_completion_days": predicted_days,
        "weak_areas": weak_areas,
        "last_activity_at": last_activity,
    })

    return JsonResponse({
        "total_time_minutes": total_time_seconds // 60,
        "topics_completed": topics_completed,
        "topics_total": topics_total,
        "completion_rate": round(completion_rate, 1),
        "average_test_score": round(avg_score, 1),
        "weak_areas": weak_areas,
        "predicted_completion_days": predicted_days,
        "days_active": days_active,
        "last_activity": last_activity.isoformat() if last_activity else None,
    })


@require_GET
def daily_metrics(request, doc_id):
    """Daily learning metrics for the past 30 days, computed live (zero-filled)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    _, error = _load_path(request, doc_id)
    if error:
        return error

    today = timezone.now().date()
    start_date = today - timedelta(days=29)

    focus_minutes = {
        row["created_at__date"]: (row["total"] or 0) // 60
        for row in FocusSession.objects.filter(
            user=request.user, path_id=doc_id, created_at__date__gte=start_date
        ).values("created_at__date").annotate(total=Sum("seconds"))
    }
    topics_done = {
        row["updated_at__date"]: row["c"]
        for row in PathProgress.objects.filter(
            user=request.user, path_id=doc_id, done=True, updated_at__date__gte=start_date
        ).values("updated_at__date").annotate(c=Count("id"))
    }
    tests_taken = {
        row["created_at__date"]: row["c"]
        for row in TestResult.objects.filter(
            user=request.user, path_id=doc_id, created_at__date__gte=start_date
        ).values("created_at__date").annotate(c=Count("id"))
    }

    metrics = []
    for offset in range(30):
        day = start_date + timedelta(days=offset)
        metrics.append({
            "date": day.isoformat(),
            "time_minutes": focus_minutes.get(day, 0),
            "topics_completed": topics_done.get(day, 0),
            "tests_taken": tests_taken.get(day, 0),
        })

    return JsonResponse({"metrics": metrics})


@require_GET
def learning_velocity(request, doc_id):
    """Calculate learning velocity (topics per week)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    _, error = _load_path(request, doc_id)
    if error:
        return error

    week_ago = timezone.now() - timedelta(days=7)

    topics_this_week = PathProgress.objects.filter(
        user=request.user,
        path_id=doc_id,
        done=True,
        updated_at__gte=week_ago
    ).count()

    return JsonResponse({
        "topics_per_week": topics_this_week,
        "estimated_completion_weeks": _estimate_weeks_to_completion(request.user, doc_id),
    })


@require_GET
def cohort_comparison(request, doc_id):
    """Compare user's progress to everyone else on the same path (computed live)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    _, error = _load_path(request, doc_id)
    if error:
        return error

    uid = request.user.id

    user_times = {
        row["user"]: (row["total"] or 0) // 60
        for row in FocusSession.objects.filter(
            path_id=doc_id
        ).values("user").annotate(total=Sum("seconds"))
    }
    user_topics = {
        row["user"]: row["c"]
        for row in PathProgress.objects.filter(
            path_id=doc_id, done=True
        ).values("user").annotate(c=Count("id"))
    }

    cohort_ids = set(user_times) | set(user_topics) | {uid}
    user_times.setdefault(uid, 0)
    user_topics.setdefault(uid, 0)

    user_time = user_times[uid]
    user_topics_done = user_topics[uid]
    avg_time = sum(user_times.get(i, 0) for i in cohort_ids) / len(cohort_ids)
    avg_topics = sum(user_topics.get(i, 0) for i in cohort_ids) / len(cohort_ids)
    percentile = _calculate_percentile(user_time, [user_times.get(i, 0) for i in cohort_ids])

    _upsert_analytics(request.user, doc_id, {
        "total_time_minutes": user_time,
        "topics_completed": user_topics_done,
        "cohort_percentile": percentile,
    })

    return JsonResponse({
        "user_time_minutes": user_time,
        "cohort_avg_time_minutes": round(avg_time, 1),
        "user_topics_completed": user_topics_done,
        "cohort_avg_topics": round(avg_topics, 1),
        "percentile": percentile,
        "cohort_size": len(cohort_ids),
    })


def _identify_weak_areas(user, path_id, path):
    """Identify phases where the user's average test score is below 70%."""
    weak_areas = []
    phases = path_phases(path)

    test_results = TestResult.objects.filter(
        user=user, path_id=path_id
    ).values('phase_idx').annotate(avg_score=Avg('percent'))

    for result in test_results:
        avg = result['avg_score']
        if avg is None or avg >= 70:
            continue
        idx = result.get('phase_idx')
        if idx is not None and 0 <= idx < len(phases):
            title = phases[idx].get('title') or f"Phase {idx + 1}"
        elif idx is not None:
            title = f"Phase {idx + 1}"
        else:
            title = "Overall"
        weak_areas.append({
            "phase": title,
            "avg_score": round(avg, 1),
        })

    return weak_areas


def _predict_completion(completed, total, days_active):
    """Predict days to completion based on current pace."""
    if days_active == 0 or completed == 0:
        return None

    remaining = total - completed
    pace = completed / days_active

    if pace == 0 or remaining <= 0:
        return None

    return int(remaining / pace)


def _estimate_weeks_to_completion(user, path_id):
    """Estimate weeks to complete path from the last week's pace."""
    week_ago = timezone.now() - timedelta(days=7)

    topics_this_week = PathProgress.objects.filter(
        user=user,
        path_id=path_id,
        done=True,
        updated_at__gte=week_ago
    ).count()

    if topics_this_week == 0:
        return None

    remaining = PathProgress.objects.filter(
        user=user,
        path_id=path_id,
        done=False
    ).count()

    if remaining <= 0:
        return 0

    return max(1, int(remaining / topics_this_week))


def _calculate_percentile(value, all_values):
    """Calculate percentile rank."""
    all_values = list(all_values)
    if not all_values:
        return 50

    count_below = sum(1 for v in all_values if v < value)
    percentile = (count_below / len(all_values)) * 100

    return int(percentile)

"""Aggregated study stats: daily activity, streaks."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import F

from .models import PathProgress, StudyActivity

User = get_user_model()


def record_activity(user, kind, count=1, day=None):
    if user is None or not user.is_authenticated:
        return
    day = day or date.today()
    row, created = StudyActivity.objects.get_or_create(
        user=user, date=day, kind=kind,
        defaults={"count": count},
    )
    if not created:
        StudyActivity.objects.filter(pk=row.pk).update(count=F("count") + count)


def _activity_map(user, start, end):
    rows = StudyActivity.objects.filter(user=user, date__gte=start, date__lte=end)
    totals = {}
    kinds = {}
    for row in rows:
        totals[row.date] = totals.get(row.date, 0) + row.count
        kinds.setdefault(row.date.isoformat(), {})[row.kind] = row.count
    return totals, kinds


def activity_series(user, days=371, today=None):
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    totals, kinds = _activity_map(user, start, today)
    series = []
    for i in range(days):
        d = start + timedelta(days=i)
        series.append({
            "date": d.isoformat(),
            "count": totals.get(d, 0),
            "kinds": kinds.get(d.isoformat(), {}),
        })
    return series


def _streak_from_dates(active):
    """active: set of ISO date strings. Returns (current, longest)."""
    if not active:
        return 0, 0
    current = 0
    cursor = date.today()
    while cursor.isoformat() in active:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    run = 0
    ordered = sorted(active)
    prev = None
    for iso in ordered:
        d = date.fromisoformat(iso)
        if prev is not None and (d - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = d
    return current, longest


def streaks(user):
    if user is None or not user.is_authenticated:
        return {"current": 0, "longest": 0, "active_days": 0}
    today = date.today()
    start = today - timedelta(days=400)
    rows = StudyActivity.objects.filter(user=user, date__gte=start).values_list("date", flat=True)
    active = {d.isoformat() for d in rows}

    progress_dates = PathProgress.objects.filter(
        user=user, done=True, updated_at__date__gte=start,
    ).values_list("updated_at", flat=True)
    active |= {dt.date().isoformat() for dt in progress_dates}

    current, longest = _streak_from_dates(active)
    return {"current": current, "longest": longest, "active_days": len(active)}

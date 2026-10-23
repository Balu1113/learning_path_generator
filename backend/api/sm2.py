"""SM-2 spaced repetition scheduling (SuperMemo 2)."""
from datetime import datetime, timedelta, timezone

MIN_EASE = 1.3
DEFAULT_EASE = 2.5

RATING_AGAIN = 0
RATING_HARD = 1
RATING_GOOD = 2
RATING_EASY = 3

_RATING_TO_QUALITY = {
    RATING_AGAIN: 0,
    RATING_HARD: 3,
    RATING_GOOD: 4,
    RATING_EASY: 5,
}


def clamp_rating(rating) -> int:
    try:
        r = int(rating)
    except (TypeError, ValueError):
        return RATING_GOOD
    return max(RATING_AGAIN, min(RATING_EASY, r))


def sm2(ease, interval_days, reps, lapses, rating, now=None):
    """Advance one card review. Returns (ease, interval_days, reps, lapses, due_at)."""
    q = _RATING_TO_QUALITY[clamp_rating(rating)]
    now = now or datetime.now(tz=timezone.utc)
    try:
        ease = float(ease)
    except (TypeError, ValueError):
        ease = DEFAULT_EASE
    try:
        interval = float(interval_days or 0)
    except (TypeError, ValueError):
        interval = 0.0
    reps = int(reps or 0)
    lapses = int(lapses or 0)

    if q < 3:
        lapses += 1
        reps = 0
        interval = 0.0
        due = now + timedelta(minutes=10)
    else:
        reps += 1
        if reps == 1:
            interval = 1.0
        elif reps == 2:
            interval = 6.0
        else:
            interval = max(1.0, round(interval * ease))
        ease = ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        ease = max(MIN_EASE, ease)
        due = now + timedelta(days=interval)

    ease = round(ease, 2)
    interval = round(interval, 2)
    return ease, interval, reps, lapses, due

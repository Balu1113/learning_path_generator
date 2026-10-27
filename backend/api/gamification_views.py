import json
import logging
import re
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from .models import (
    UserLevel, XPTransaction, DailyQuest, QuestProgress,
    SeasonalChallenge, ChallengeParticipation, Leaderboard, LearningStreak
)
from .views import _json_body, _user_id
from .schedule_builder import structured_phases
from memory.vector_store import vector_memory
from chains.path_generator import (
    generate_daily_quests as _ai_generate_daily_quests,
    parse_markdown_phases,
    phase_from_markdown_body,
)

logger = logging.getLogger(__name__)


@require_GET
def user_level(request):
    """Get user's current level and XP."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    level, created = UserLevel.objects.get_or_create(user=request.user)
    
    return JsonResponse({
        "xp_total": level.xp_total,
        "level": level.level,
        "xp_to_next_level": level.xp_to_next_level,
        "xp_progress": max(0, level.xp_total % level.xp_to_next_level),
    })


@require_GET
def xp_history(request):
    """Get user's recent XP transactions."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    transactions = XPTransaction.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    return JsonResponse({
        "transactions": [
            {
                "activity": t.activity,
                "xp_amount": t.xp_amount,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ]
    })


@require_GET
def daily_quests(request):
    """Get today's quests and user's progress (answers are never sent to the client)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    today = timezone.now().date()
    quests = DailyQuest.objects.filter(active_date=today)

    result = []
    for quest in quests:
        progress, _ = QuestProgress.objects.get_or_create(user=request.user, quest=quest)
        result.append(_quest_payload(quest, progress))

    return JsonResponse({"quests": result})


def _quest_payload(quest, progress):
    """Serialize a quest for the client, stripping correct answers."""
    requirement = quest.requirement if isinstance(quest.requirement, dict) else {}
    questions = requirement.get("questions") if isinstance(requirement.get("questions"), list) else None
    safe_questions = [
        {"index": i, "question": str(q.get("question") or "")}
        for i, q in enumerate(questions or [])
        if isinstance(q, dict) and q.get("question")
    ]
    return {
        "id": quest.id,
        "title": quest.title,
        "description": quest.description,
        "difficulty": quest.difficulty,
        "xp_reward": quest.xp_reward,
        "is_quiz": requirement.get("type") == "quiz" and bool(safe_questions),
        "questions": safe_questions,
        "progress_count": progress.progress_count,
        "target_count": _quest_target_count(quest),
        "completed": progress.completed,
    }


def _normalize_answer(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _answer_matches(user_answer, question_obj):
    """Fuzzy check of a user answer against the expected answer and alternates."""
    ua = _normalize_answer(user_answer)
    if not ua:
        return False
    candidates = [question_obj.get("answer", "")]
    alternates = question_obj.get("alternates")
    if isinstance(alternates, list):
        candidates.extend(alternates)
    for candidate in candidates:
        cn = _normalize_answer(str(candidate))
        if not cn:
            continue
        if ua == cn:
            return True
        if len(cn) >= 4 and (cn in ua or ua in cn):
            return True
    return False


@csrf_protect
@require_POST
def complete_quest(request, quest_id):
    """Submit an answer (quiz quests) or record activity progress."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    try:
        quest = DailyQuest.objects.get(id=quest_id)
    except DailyQuest.DoesNotExist:
        return JsonResponse({"error": "Quest not found"}, status=404)

    progress, _ = QuestProgress.objects.get_or_create(user=request.user, quest=quest)

    if progress.completed:
        return JsonResponse({
            "completed": True,
            "already_completed": True,
            "xp_earned": 0,
            "progress_count": progress.progress_count,
            "target_count": _quest_target_count(quest),
        })

    data = _json_body(request)
    requirement = quest.requirement if isinstance(quest.requirement, dict) else {}
    questions = requirement.get("questions") if isinstance(requirement.get("questions"), list) else None
    is_quiz = requirement.get("type") == "quiz" and bool(questions)

    if is_quiz:
        idx = progress.progress_count
        if idx >= len(questions):
            idx = len(questions) - 1
        current = questions[idx]
        answer = str(data.get("answer") or "").strip()
        if not answer:
            return JsonResponse({"error": "answer is required for quiz quests"}, status=400)

        if not _answer_matches(answer, current):
            return JsonResponse({
                "completed": False,
                "correct": False,
                "xp_earned": 0,
                "progress_count": progress.progress_count,
                "target_count": len(questions),
            })

        progress.progress_count += 1
        done = progress.progress_count >= len(questions)
        if done:
            progress.completed = True
            progress.completed_at = timezone.now()
            _award_xp(request.user, 'quest_complete', quest.xp_reward, f"Completed: {quest.title}")
        progress.save()

        next_question = None
        if not done and progress.progress_count < len(questions):
            next_question = {
                "index": progress.progress_count,
                "question": str(questions[progress.progress_count].get("question") or ""),
            }

        return JsonResponse({
            "completed": progress.completed,
            "correct": True,
            "xp_earned": quest.xp_reward if done else 0,
            "progress_count": progress.progress_count,
            "target_count": len(questions),
            "next_question": next_question,
        })

    # Non-quiz (activity-style) quests: count completions toward the target
    target = _quest_target_count(quest)
    if progress.progress_count < target:
        progress.progress_count += 1
        progress.save()

    if progress.progress_count >= target:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()
        _award_xp(request.user, 'quest_complete', quest.xp_reward, f"Completed: {quest.title}")
        xp_earned = quest.xp_reward
    else:
        xp_earned = 0

    return JsonResponse({
        "completed": progress.completed,
        "correct": True,
        "xp_earned": xp_earned,
        "progress_count": progress.progress_count,
        "target_count": target,
    })


def _quest_target_count(quest):
    """Target progress count: number of quiz questions, or requirement.count (default 1)."""
    requirement = quest.requirement if isinstance(quest.requirement, dict) else {}
    questions = requirement.get("questions")
    if requirement.get("type") == "quiz" and isinstance(questions, list) and questions:
        return len(questions)
    try:
        return max(1, int(requirement.get("count", 1)))
    except (TypeError, ValueError):
        return 1


_FALLBACK_QUEST_TEMPLATES = (
    {"title": "Review today's notes", "description": "Spend 15 minutes reviewing notes and flashcards from your {goal} path.", "difficulty": "easy", "xp_reward": 15, "requirement": {"type": "activity_count", "count": 1}},
    {"title": "Complete one practice activity", "description": "Finish one lesson, quiz, or practice exercise on your {goal} path.", "difficulty": "medium", "xp_reward": 30, "requirement": {"type": "activity_count", "count": 1}},
    {"title": "Focused deep-work session", "description": "Do a 45-minute distraction-free study session on your {goal} path.", "difficulty": "hard", "xp_reward": 60, "requirement": {"type": "activity_count", "count": 1}},
    {"title": "Knowledge check", "description": "Answer 5 review questions about {goal} concepts you've already studied.", "difficulty": "medium", "xp_reward": 25, "requirement": {"type": "activity_count", "count": 2}},
    {"title": "Apply what you learned", "description": "Write a short summary or do a tiny exercise applying one {goal} concept.", "difficulty": "hard", "xp_reward": 50, "requirement": {"type": "activity_count", "count": 1}},
)


def _user_owned_paths(user, n=200):
    try:
        paths = vector_memory.get_recent_paths(n=n)
    except Exception:
        return []
    uid = str(user.id)
    return [p for p in paths if (p.get("metadata") or {}).get("owner") == uid]


def _path_topics_text(path):
    """Phase/topic summary text for a structured or markdown path document."""
    meta = path.get("metadata") or {}
    lines = []
    try:
        if meta.get("format") == "structured":
            for i, ph in enumerate(structured_phases(path)):
                topics = [t for t in (ph.get("topics") or []) if t.get("title")]
                if not topics:
                    continue
                lines.append(f"Phase {i + 1}: {ph.get('title', f'Phase {i + 1}')}")
                lines.extend(f"- {t.get('title')}: {t.get('details', '')}" for t in topics)
        else:
            for i, ph in enumerate(parse_markdown_phases(path.get("content") or "")):
                body = phase_from_markdown_body(ph)
                if not body.get("topics_text"):
                    continue
                lines.append(f"Phase {i + 1}: {body.get('title', f'Phase {i + 1}')}")
                lines.append(body["topics_text"])
    except Exception:
        return ""
    return "\n".join(lines)[:6000]


def _user_learning_context(user):
    """Goal and topic text from the user's most recent learning paths."""
    paths = _user_owned_paths(user)
    goal = "general learning"
    topic_chunks = []
    for p in reversed(paths[-5:]):
        meta = p.get("metadata") or {}
        if goal == "general learning" and (meta.get("goal") or "").strip():
            goal = meta["goal"].strip()[:300]
        chunk = _path_topics_text(p)
        if chunk:
            header = f"Path: {meta.get('goal') or 'learning path'}"
            topic_chunks.append(f"{header}\n{chunk}")
    return goal, "\n\n".join(topic_chunks)[:8000]


def _recent_question_texts(today):
    """Question text from today's quiz quests, to avoid repeats."""
    texts = []
    for quest in DailyQuest.objects.filter(active_date=today):
        requirement = quest.requirement if isinstance(quest.requirement, dict) else {}
        for q in requirement.get("questions") or []:
            if isinstance(q, dict) and q.get("question"):
                texts.append(str(q["question"]))
        texts.append(quest.title)
    return texts


@csrf_protect
@require_POST
def generate_daily_quests(request):
    """Generate today's daily quiz quests from the user's path topics (AI, with template fallback)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    data = _json_body(request)
    try:
        count = max(1, min(6, int(data.get("count", 3))))
    except (TypeError, ValueError):
        count = 3

    context_goal, topics_text = _user_learning_context(request.user)
    goal = str(data.get("goal") or "").strip()[:300] or context_goal

    today = timezone.now().date()
    existing_titles = set(
        DailyQuest.objects.filter(active_date=today).values_list("title", flat=True)
    )

    level, _ = UserLevel.objects.get_or_create(user=request.user)

    quests_data = None
    source = "fallback"
    try:
        result = _ai_generate_daily_quests(
            goal=goal,
            level=level.level,
            count=count,
            topics_text=topics_text,
            avoid=_recent_question_texts(today),
        )
        raw_quests = result.get("quests") if isinstance(result, dict) else None
        if isinstance(raw_quests, list) and raw_quests:
            quests_data = raw_quests
            source = "ai"
    except Exception as e:
        logger.warning("AI daily quest generation failed, using fallback: %s", e)

    if quests_data is None:
        quests_data = [
            {**t, "description": t["description"].format(goal=goal)}
            for t in _FALLBACK_QUEST_TEMPLATES[:count]
        ]

    created = 0
    for q in quests_data[:count]:
        title = str(q.get("title") or "").strip()[:255]
        if not title or title in existing_titles:
            continue
        difficulty = q.get("difficulty")
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"
        try:
            xp_reward = int(q.get("xp_reward") or 25)
        except (TypeError, ValueError):
            xp_reward = 25
        xp_reward = max(5, min(200, xp_reward))

        # Quiz quests: store questions (with answers) in the requirement JSON
        raw_questions = q.get("questions")
        questions = []
        if isinstance(raw_questions, list):
            for item in raw_questions[:5]:
                if not isinstance(item, dict):
                    continue
                question = str(item.get("question") or "").strip()
                answer = str(item.get("answer") or "").strip()
                if not question or not answer:
                    continue
                alternates = [
                    str(a).strip()
                    for a in (item.get("alternates") or [])
                    if isinstance(a, str) and a.strip()
                ][:3]
                questions.append({"question": question[:500], "answer": answer[:200], "alternates": alternates})

        if questions:
            requirement = {"type": "quiz", "count": len(questions), "questions": questions}
        else:
            requirement = q.get("requirement")
            if not isinstance(requirement, dict):
                requirement = {"type": "activity_count", "count": 1}

        DailyQuest.objects.create(
            title=title,
            description=str(q.get("description") or "")[:2000],
            difficulty=difficulty,
            xp_reward=xp_reward,
            requirement=requirement,
            active_date=today,
        )
        existing_titles.add(title)
        created += 1

    quests = DailyQuest.objects.filter(active_date=today)
    result = []
    for quest in quests:
        progress, _ = QuestProgress.objects.get_or_create(user=request.user, quest=quest)
        result.append(_quest_payload(quest, progress))

    return JsonResponse({"quests": result, "created": created, "source": source})


@require_GET
def seasonal_challenges(request):
    """Get active seasonal challenges."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    today = timezone.now().date()
    challenges = SeasonalChallenge.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    )
    
    result = []
    for challenge in challenges:
        participation, _ = ChallengeParticipation.objects.get_or_create(
            user=request.user, challenge=challenge
        )
        result.append({
            "id": challenge.id,
            "title": challenge.title,
            "description": challenge.description,
            "start_date": challenge.start_date.isoformat(),
            "end_date": challenge.end_date.isoformat(),
            "xp_reward": challenge.xp_reward,
            "progress": participation.progress,
            "completed": participation.completed,
            "rank": participation.rank,
        })
    
    return JsonResponse({"challenges": result})


@require_GET
def leaderboard(request):
    """Get leaderboard for a scope and path."""
    scope = request.GET.get('scope', 'global')
    path_id = request.GET.get('path_id', '')
    
    if scope not in ['global', 'cohort', 'friends']:
        scope = 'global'
    
    query = Leaderboard.objects.filter(scope=scope)
    if path_id:
        query = query.filter(path_id=path_id)
    
    entries = query.order_by('rank')[:100]
    
    return JsonResponse({
        "leaderboard": [
            {
                "rank": e.rank,
                "username": e.user.username,
                "score": e.score,
            }
            for e in entries
        ]
    })


@require_GET
def learning_streak(request):
    """Get user's learning streak."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    
    return JsonResponse({
        "current_streak_days": streak.current_streak_days,
        "longest_streak_days": streak.longest_streak_days,
        "last_activity_date": streak.last_activity_date.isoformat() if streak.last_activity_date else None,
    })


def _award_xp(user, activity, xp_amount, description=""):
    """Award XP to user and update level."""
    XPTransaction.objects.create(
        user=user,
        activity=activity,
        xp_amount=xp_amount,
        description=description
    )
    
    level, _ = UserLevel.objects.get_or_create(user=user)
    level.xp_total += xp_amount
    
    level_thresholds = {
        'novice': 0,
        'beginner': 1000,
        'intermediate': 3000,
        'advanced': 7000,
        'expert': 15000,
    }
    
    for level_name, threshold in sorted(level_thresholds.items(), key=lambda x: x[1], reverse=True):
        if level.xp_total >= threshold:
            level.level = level_name
            break
    
    level.save()
    
    _update_streak(user)


def _update_streak(user):
    """Update user's learning streak."""
    streak, _ = LearningStreak.objects.get_or_create(user=user)
    today = timezone.now().date()
    
    if streak.last_activity_date is None:
        streak.current_streak_days = 1
        streak.longest_streak_days = 1
    elif streak.last_activity_date == today:
        pass
    elif streak.last_activity_date == today - timedelta(days=1):
        streak.current_streak_days += 1
        if streak.current_streak_days > streak.longest_streak_days:
            streak.longest_streak_days = streak.current_streak_days
    else:
        streak.current_streak_days = 1
    
    streak.last_activity_date = today
    streak.save()

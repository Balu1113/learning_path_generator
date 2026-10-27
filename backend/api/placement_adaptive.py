"""Adaptive placement: one-question-at-a-time flow with early stopping.

Decision rules (deterministic and auditable):
- Serve questions in easy -> medium -> hard order.
- The first miss sets the ceiling: miss easy => beginner (stop), miss medium =>
  intermediate (stop), miss hard => intermediate (stop).
- All of a band correct => advance to the next band with unanswered questions.
- All hard correct => advanced. If later bands are empty in the pool, the best
  justified level from completed bands is used (all-easy => intermediate,
  all-easy+medium => advanced).

The flow never asks more than the pool contains and skips unanswered bands
that do not exist.
"""

DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}
BANDS = ("easy", "medium", "hard")
# A miss sets the ceiling for the session: stumbling on hard still means the
# learner cleared easy+medium but cannot claim advanced.
MISS_LEVEL = {"easy": "beginner", "medium": "intermediate", "hard": "intermediate"}


def normalize_question(raw, index: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    question = str(raw.get("question") or "").strip()
    options = [str(o) for o in (raw.get("options") or []) if str(o).strip()]
    if not question or len(options) < 2:
        return None
    try:
        answer_index = int(raw.get("answer_index", 0))
    except (TypeError, ValueError):
        answer_index = 0
    if answer_index < 0 or answer_index >= len(options):
        answer_index = 0
    difficulty = str(raw.get("difficulty") or "medium").strip().lower()
    if difficulty not in DIFFICULTY_RANK:
        difficulty = "medium"
    return {
        "id": str(raw.get("id") or f"q{index + 1}"),
        "question": question[:1000],
        "options": options[:6],
        "answer_index": answer_index,
        "difficulty": difficulty,
    }


def prepare_pool(raw_questions: list, cap: int = 10) -> list:
    cleaned = [q for q in (normalize_question(r, i) for i, r in enumerate(raw_questions or [])) if q]
    cleaned.sort(key=lambda q: (DIFFICULTY_RANK[q["difficulty"]], q["id"]))
    return cleaned[: max(1, cap)]


def safe_question(q: dict) -> dict:
    return {"id": q["id"], "question": q["question"], "options": q["options"], "difficulty": q["difficulty"]}


def new_state(goal: str, pool: list) -> dict:
    return {
        "goal": goal,
        "questions": pool,
        "answers": {},  # question_id -> selected index
        "phase": "easy",
        "done": False,
        "level": None,
    }


def _band_questions(state: dict, band: str) -> list:
    return [q for q in state["questions"] if q["difficulty"] == band]


def _first_unanswered(state: dict, band: str) -> dict | None:
    for q in _band_questions(state, band):
        if q["id"] not in state["answers"]:
            return q
    return None


def _finalize(state: dict, level: str) -> dict:
    state["done"] = True
    state["level"] = level
    return state


def _advance(state: dict) -> dict:
    """Move to the next band with unanswered questions, or finish.

    If later bands are empty (LLM omitted them), justify the best level the
    completed evidence supports: all-easy => intermediate, all-easy+medium =>
    advanced.
    """
    idx = BANDS.index(state["phase"]) + 1
    while idx < len(BANDS):
        band = BANDS[idx]
        if _first_unanswered(state, band) is not None:
            state["phase"] = band
            return state
        idx += 1
    level = "advanced" if state["phase"] in ("medium", "hard") else "intermediate"
    return _finalize(state, level)


def current_question(state: dict) -> dict | None:
    if state["done"]:
        return None
    nxt = _first_unanswered(state, state["phase"])
    if nxt is not None:
        return nxt
    _advance(state)
    if state["done"]:
        return None
    return _first_unanswered(state, state["phase"])


def record_answer(state: dict, question_id: str, answer_index: int) -> dict:
    """Record one answer and apply the stopping/advancement rules. Mutates state."""
    if state["done"]:
        return state
    question = next((q for q in state["questions"] if q["id"] == question_id), None)
    if question is None:
        raise KeyError(f"unknown question id: {question_id}")
    if question_id in state["answers"]:
        raise ValueError("question already answered")
    state["answers"][question_id] = answer_index

    band = question["difficulty"]
    correct = answer_index == question["answer_index"]

    if not correct:
        # Confidence rule: the first miss sets the ceiling for this session.
        return _finalize(state, MISS_LEVEL[band])

    remaining = _first_unanswered(state, band)
    if remaining is not None:
        return state

    # Band fully correct -> move up.
    if band == "hard":
        return _finalize(state, "advanced")
    return _advance(state)


def session_summary(state: dict) -> dict:
    asked = [q for q in state["questions"] if q["id"] in state["answers"]]
    correct = sum(1 for q in asked if state["answers"][q["id"]] == q["answer_index"])
    missed = [
        {
            "id": q["id"],
            "question": q["question"],
            "difficulty": q["difficulty"],
            "correct_index": q["answer_index"],
            "user_index": state["answers"][q["id"]],
        }
        for q in asked
        if state["answers"][q["id"]] != q["answer_index"]
    ]
    total = len(asked)
    return {
        "score": correct,
        "total": total,
        "percent": int(round(100 * correct / total)) if total else 0,
        "suggested_level": state["level"],
        "missed": missed,
        "skipped": len(state["questions"]) - total,
    }

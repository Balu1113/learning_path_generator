from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re
from config import GEMINI_API_KEY, GEMINI_MODEL


PATH_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert Learning Path Generator AI. You create detailed, structured, and personalized learning roadmaps using YOUR OWN knowledge.

When given a learning goal, you:
1. Break down the goal into logical phases (from beginner to advanced)
2. For each phase, list specific topics with estimated time
3. Recommend real, specific resources (courses, books, platforms, YouTube channels, websites)
4. Include practical projects to solidify learning
5. Provide a total estimated timeline
6. Fit the phases into the requested timeframe — the total timeline must not exceed {months} months

Always structure your response as a clear markdown roadmap with phases, topics, time estimates, and resources.
Use your knowledge of real courses, books, and platforms — be specific and actionable."""),
    ("human", """Generate a detailed learning path for the following goal:

**Goal:** {goal}
**Current Level:** {current_level}
**Hours per Day:** {hours_per_day} hours
**Preferred Format:** {format_preference}
**Timeframe:** {months} months
**Target Completion Date:** {target_date}

Create a comprehensive, structured learning roadmap."""),
])

STRUCTURED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert Learning Path Generator AI. You create detailed, structured, personalized learning roadmaps using YOUR OWN knowledge.

Return ONLY a valid JSON object (no markdown fences, no commentary) with exactly this schema:
{{
  "title": "short roadmap title",
  "summary": "2-3 sentence overview",
  "total_weeks": <number>,
  "phases": [
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
  ]
}}

Rules:
- 3 to 6 phases; 3 to 6 topics per phase; 2 to 4 resources per topic
- Recommend real, specific resources (real course names, books, platforms, channels)
- Fit everything into the requested timeframe — total_weeks must not exceed the timeframe in months * 4.33
- Be specific and actionable. Output ONLY the JSON object."""),
    ("human", """Generate a detailed learning path for the following goal:

**Goal:** {goal}
**Current Level:** {current_level}
**Hours per Day:** {hours_per_day} hours
**Preferred Format:** {format_preference}
**Timeframe:** {months} months
**Target Completion Date:** {target_date}"""),
])

PLACEMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a skills assessment expert. Return ONLY a valid JSON object (no markdown fences) with this schema:
{{
  "questions": [
    {{
      "id": "q1",
      "question": "the question text",
      "options": ["option A", "option B", "option C", "option D"],
      "answer_index": <0-based index of the correct option>
    }}
  ]
}}
Create 5 multiple-choice questions to assess someone's current skill level for the given learning goal.
Questions should range from absolute-beginner to advanced concepts in that field. Exactly 4 options each."""),
    ("human", """Assess the current skill level of someone whose goal is: {goal}"""),
])

PHASE_TEST_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an assessment expert creating a quiz for one phase of a learning roadmap. Return ONLY a valid JSON object (no markdown fences) with this schema:
{{
  "questions": [
    {{
      "id": "q1",
      "question": "the question text",
      "options": ["option A", "option B", "option C", "option D"],
      "answer_index": <0-based index of the correct option>
    }}
  ]
}}
Rules:
- Create exactly {count} multiple-choice questions, exactly 4 options each
- Questions must test understanding of the topics in this phase (not other phases)
- Mix difficulty from recall to applied scenario questions
- Do NOT repeat or closely paraphrase these previously asked questions: {avoid}"""),
    ("human", """Learning goal: {goal}

Phase to test: {phase_title}
Phase description: {phase_description}

Topics covered in this phase:
{topics}"""),
])


def _llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
    )


def _chain_inputs(goal, current_level, hours_per_day, format_preference, months, target_date):
    return {
        "goal": goal,
        "current_level": current_level,
        "hours_per_day": hours_per_day,
        "format_preference": format_preference,
        "months": months,
        "target_date": target_date or "not set",
    }


def create_path_chain():
    return PATH_GENERATION_PROMPT | _llm() | StrOutputParser()


def generate_learning_path(
    goal: str,
    current_level: str = "beginner",
    hours_per_day: int = 2,
    format_preference: str = "courses and hands-on projects",
    months: int = 6,
    target_date: str = "",
) -> str:
    chain = create_path_chain()
    return chain.invoke(_chain_inputs(goal, current_level, hours_per_day, format_preference, months, target_date))


def _chunk_text(chunk) -> str:
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", "") or "")
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
        return "".join(parts)
    return str(content) if content else ""


def stream_learning_path(
    goal: str,
    current_level: str = "beginner",
    hours_per_day: int = 2,
    format_preference: str = "courses and hands-on projects",
    months: int = 6,
    target_date: str = "",
):
    chain = PATH_GENERATION_PROMPT | _llm()
    for chunk in chain.stream(_chain_inputs(goal, current_level, hours_per_day, format_preference, months, target_date)):
        text = _chunk_text(chunk)
        if text:
            yield text


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def generate_learning_path_structured(
    goal: str,
    current_level: str = "beginner",
    hours_per_day: int = 2,
    format_preference: str = "courses and hands-on projects",
    months: int = 6,
    target_date: str = "",
) -> dict:
    chain = STRUCTURED_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke(_chain_inputs(goal, current_level, hours_per_day, format_preference, months, target_date))
    return _parse_json(raw)


def generate_placement_quiz(goal: str) -> dict:
    chain = PLACEMENT_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({"goal": goal})
    return _parse_json(raw)


def generate_phase_quiz(goal: str, phase: dict, count: int = 5, avoid: list | None = None) -> dict:
    topics = phase.get("topics_text") or "\n".join(
        f"- {t.get('title', '')}: {t.get('details', '')}"
        for t in phase.get("topics", [])
    ) or "- (general phase knowledge)"
    avoid_list = [a for a in (avoid or []) if a][:20]
    chain = PHASE_TEST_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "goal": goal,
        "phase_title": phase.get("title", "Phase"),
        "phase_description": phase.get("description", ""),
        "topics": topics,
        "count": max(1, min(10, count)),
        "avoid": avoid_list if avoid_list else "none yet",
    })
    return _parse_json(raw)


FLASHCARD_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at creating study flashcards for spaced repetition review. Return ONLY a valid JSON object (no markdown fences) with this schema:
{{
  "cards": [
    {{"front": "short question or term", "back": "concise, complete answer or explanation"}}
  ]
}}
Rules:
- Create exactly {count} cards
- Fronts must be answerable in one sentence and test real understanding, not trivia
- Backs must be self-contained (the reviewer must not need the path open)
- Cover every topic listed below evenly
- No duplicates and no near-duplicates of: {avoid}"""),
    ("human", """Learning goal: {goal}

Phase: {phase_title}
Topics in this phase:
{topics}"""),
])


def generate_flashcards(goal: str, phase_title: str, topics_text: str, count: int = 12, avoid: list | None = None) -> dict:
    chain = FLASHCARD_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "goal": goal,
        "phase_title": phase_title,
        "topics": topics_text or "- (general phase knowledge)",
        "count": max(1, min(40, count)),
        "avoid": [a for a in (avoid or []) if a][:40] or "none yet",
    })
    return _parse_json(raw)


STUDY_NOTES_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert educator writing in-depth study notes for ONE topic from a learner's personalized roadmap. Output ONLY markdown — no preamble, no code fences around the whole answer.

Write for a motivated self-learner. Be concrete, use real examples, and explain the WHY, not just the what. Never pad with generic filler.

For level 1 (core notes), use exactly this structure:

## <Topic> — Core Notes

### The big idea
Intuitive explanation of what this concept is and why it matters (2-3 real paragraphs).

### How it works
Precise step-by-step explanation. Include a small formula, pseudocode, or numbered steps where natural.

### Worked example
One concrete worked example with actual values, numbers, or short code-like snippets.

### Common misconceptions
2-4 misconceptions, each stated as a claim followed by the correction.

### Key takeaways
5-7 bullets the learner must remember.

### Glossary
4-6 bullets of the form "term — short definition".

For level 2 and deeper, use exactly this structure and go substantially deeper (advanced nuances, edge cases, math intuition, connections to other topics, real-world failure stories, complexity/performance angles):

## <Topic> — Deep Dive {level}

### Advanced insights
### Edge cases and failure modes
### Connections
### Practice challenges
2-3 concrete exercises, each with a short hint (not the full solution).

Rules:
- 450-800 words per level
- Never repeat or restate content already covered in: {covered}
- Calibrate depth to the learner's overall goal: {goal}
- Use ## and ### markdown headings exactly as specified"""),
    ("human", """Learning goal: {goal}

Phase: {phase_title}
Topic: {topic_title}
Topic details: {topic_details}
Level: {level}

Write the study notes now."""),
])


def generate_study_notes(
    goal: str,
    phase_title: str,
    topic_title: str,
    topic_details: str = "",
    level: int = 1,
    covered: list[str] | None = None,
) -> str:
    chain = STUDY_NOTES_PROMPT | _llm() | StrOutputParser()
    covered_list = [c for c in (covered or []) if c][:12]
    raw = chain.invoke({
        "goal": goal,
        "phase_title": phase_title or "Phase",
        "topic_title": topic_title,
        "topic_details": topic_details or "(none provided)",
        "level": max(1, int(level)),
        "covered": "\n".join(f"- {c}" for c in covered_list) if covered_list else "nothing yet — this is the first level",
    })
    return raw.strip()


_PHASE_HEADING_RE = re.compile(
    r"^\s{0,3}(#{2,4})\s+(.*phase.*?)\s*#*\s*$",
    re.IGNORECASE,
)


def parse_markdown_phases(markdown: str) -> list[dict]:
    """Extract phases from a markdown roadmap by splitting on phase headings."""
    lines = (markdown or "").splitlines()
    headings = []
    for i, line in enumerate(lines):
        m = _PHASE_HEADING_RE.match(line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))

    if not headings:
        return []

    starts = [h[0] for h in headings]
    ends = starts[1:] + [len(lines)]
    phases = []
    for (line_no, _level, title), end in zip(headings, ends):
        body = "\n".join(lines[line_no + 1:end]).strip()
        cleaned = title.strip().strip("*_").strip()
        cleaned = re.sub(r"^(phase\s*\d+\s*[:\-–—]\s*)", "", cleaned, flags=re.IGNORECASE).strip()
        phases.append({
            "title": cleaned or title,
            "raw": body,
            "description": "",
            "topics_text": "",
        })
    return phases


def phase_from_markdown_body(phase: dict) -> dict:
    """Summarize a markdown phase body into title/description/topics_text for the quiz prompt."""
    body = phase.get("raw", "").strip()
    topics = [
        line.strip()
        for line in body.splitlines()
        if line.strip().startswith(("-", "*", "•"))
    ]
    topics_text = "\n".join(topics[:30]) or body[:1500] or "- (general phase knowledge)"
    description = ""
    for line in body.splitlines():
        s = line.strip()
        if s and not s.startswith(("#", "-", "*", "•", "|", "```")):
            description = s[:300]
            break
    return {
        "title": phase.get("title", "Phase"),
        "description": description,
        "topics_text": topics_text,
    }

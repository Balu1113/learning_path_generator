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
    ("system", """You are an expert Learning Path Generator AI. You create detailed, structured, and personalized learning roadmaps using YOUR OWN knowledge.

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
            {{"name": "resource name", "type": "course|book|video|article|tool|docs", "note": "one short sentence", "verified": true|false}}
          ]
        }}
      ]
    }}
  ]
}}

Rules:
- 3 to 6 phases; 3 to 6 topics per phase; 2 to 4 resources per topic
- Recommend real, specific resources (real course names, books, platforms, channels)
- Where a VERIFIED CATALOG entry fits a topic, prefer it and set "verified": true for that resource; otherwise recommend from your own knowledge with "verified": false
- Never mark a resource verified unless you took its name from the catalog list
- Fit everything into the requested timeframe — total_weeks must not exceed the timeframe in months * 4.33
- Be specific and actionable. Output ONLY the JSON object.

VERIFIED CATALOG:
{catalog}"""),
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
      "answer_index": <0-based index of the correct option>,
      "difficulty": "easy|medium|hard"
    }}
  ]
}}
Create {count} multiple-choice questions to assess someone's current skill level for the given learning goal.
Include exactly {count_easy} easy, {count_medium} medium, and {count_hard} hard questions (4 options each).
Do NOT ask about these topics the learner has already mastered: {avoid}"""),
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

PROJECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert curriculum designer creating ONE capstone project for a phase of a learning roadmap. Return ONLY a valid JSON object (no markdown fences) with exactly this schema:
{{
  "title": "short project name",
  "brief": "3-5 sentence project brief: what to build, who it is for, and why it proves the phase skills",
  "acceptance_criteria": ["testable criterion", "testable criterion"],
  "starter_template": "markdown for a starter repository: folder structure, setup steps, interfaces/modules to implement, and what may stay as stubs",
  "rubric": [
    {{"criterion": "name", "max_points": <number>, "description": "what full marks looks like"}}
  ]
}}
Rules:
- Scope the project so this learner can finish it within the phase's estimated time ({weeks} week(s)); prefer one focused deliverable over a large system
- Exactly 4 to 7 acceptance criteria, each independently verifiable
- Rubric has 4 to 6 criteria whose max_points total exactly 100
- Starter template must be concrete: real folder layout, setup commands, and named entry points or functions to implement
- Calibrate difficulty to a {current_level} learner working through this phase"""),
    ("human", """Learning goal: {goal}
Learner level: {current_level}

Phase: {phase_title}
Phase description: {phase_description}
Estimated weeks for this phase: {weeks}

Topics in this phase:
{topics}"""),
])

PROJECT_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a rigorous but encouraging technical reviewer grading a learner's project submission against its rubric. Return ONLY a valid JSON object (no markdown fences) with exactly this schema:
{{
  "score": <integer 0-100>,
  "criteria_met": ["criterion met"],
  "criteria_missed": [{{"criterion": "name", "why": "short reason"}}],
  "review": "markdown feedback: what works, what is missing, and the 2-3 highest-leverage next steps"
}}
Rules:
- Score strictly from the rubric weights: award each criterion's points proportional to how well the submission satisfies it
- Be honest: if the submission URL or notes do not provide enough evidence to verify a criterion, do not award its points; list it under criteria_missed
- The review must be 150-400 words, concrete, and reference the learner's actual submission content
- Never invent features the learner did not mention"""),
    ("human", """Project title: {title}

Project brief:
{brief}

Acceptance criteria:
{acceptance_criteria}

Rubric:
{rubric}

Submission URL: {submission_url}
Submission notes from the learner:
{submission_notes}"""),
])


def _llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
    )


def _chain_inputs(goal, current_level, hours_per_day, format_preference, months, target_date, catalog=""):
    return {
        "goal": goal,
        "current_level": current_level,
        "hours_per_day": hours_per_day,
        "format_preference": format_preference,
        "months": months,
        "target_date": target_date or "not set",
        "catalog": catalog or "none available yet",
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
    catalog: str = "",
) -> dict:
    chain = STRUCTURED_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke(_chain_inputs(goal, current_level, hours_per_day, format_preference, months, target_date, catalog))
    return _parse_json(raw)


def generate_placement_quiz(
    goal: str,
    count_easy: int = 2,
    count_medium: int = 2,
    count_hard: int = 1,
    avoid: list | None = None,
) -> dict:
    count_easy = max(0, min(6, int(count_easy or 0)))
    count_medium = max(0, min(6, int(count_medium or 0)))
    count_hard = max(0, min(6, int(count_hard or 0)))
    total = count_easy + count_medium + count_hard
    if total == 0:
        count_easy = 2
        count_medium = 2
        count_hard = 1
        total = 5
    chain = PLACEMENT_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "goal": goal,
        "count": total,
        "count_easy": count_easy,
        "count_medium": count_medium,
        "count_hard": count_hard,
        "avoid": [a for a in (avoid or []) if a][:20] or "none",
    })
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


def generate_phase_project(
    goal: str,
    phase: dict,
    current_level: str = "beginner",
    weeks: int = 4,
) -> dict:
    topics = phase.get("topics_text") or "\n".join(
        f"- {t.get('title', '')}: {t.get('details', '')}"
        for t in (phase.get("topics") or [])
    ) or "- (general phase knowledge)"
    chain = PROJECT_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "goal": goal,
        "current_level": current_level or "beginner",
        "phase_title": phase.get("title", "Phase"),
        "phase_description": phase.get("description", ""),
        "topics": topics,
        "weeks": max(1, int(weeks or 4)),
    })
    return _parse_json(raw)


def review_phase_project(
    brief: str,
    acceptance_criteria: list,
    rubric: list,
    submission_url: str,
    submission_notes: str,
    title: str = "Project",
) -> dict:
    chain = PROJECT_REVIEW_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "title": title,
        "brief": brief or "(no brief)",
        "acceptance_criteria": "\n".join(f"- {c}" for c in (acceptance_criteria or [])) or "- (none)",
        "rubric": "\n".join(
            f"- {r.get('criterion', 'item')} ({r.get('max_points', 0)} pts): {r.get('description', '')}"
            for r in (rubric or []) if isinstance(r, dict)
        ) or "- (none)",
        "submission_url": submission_url or "(not provided)",
        "submission_notes": submission_notes or "(not provided)",
    })
    return _parse_json(raw)


JOB_TARGET_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a career-skills analyst. Given a job description or target role, extract the durable technical and professional skills required, then compare them with the learner's current mastery matrix to identify gaps.

Return ONLY a valid JSON object (no markdown fences) with exactly this schema:
{{
  "role_title": "inferred or provided role title",
  "required_skills": [
    {{"name": "Canonical skill name", "slug": "canonical-slug", "importance": "core|supporting|nice-to-have", "reason": "one sentence why this skill matters for the role"}}
  ],
  "gap_summary": "2-3 sentence plain-English summary of the learner's readiness and the most critical gaps",
  "gap_path_hint": "one sentence on the highest-leverage learning focus to close the gap fastest"
}}
Rules:
- 5 to 15 required_skills; use canonical, well-known names (e.g. "Python", "System Design", "SQL")
- importance: "core" = must-have, "supporting" = strongly preferred, "nice-to-have" = bonus
- If the job description is malformed or too short, still return a best-effort extraction with a note in gap_summary
- Never invent mastery the learner does not have; base gap analysis strictly on the provided mastery list
- Output ONLY the JSON object"""),
    ("human", """Job description or target role:
{job_description}

Learner's currently validated skills (slug list):
{validated_skills}

Learner's developing skills (slug list):
{developing_skills}"""),
])


def analyze_job_target(
    job_description: str,
    validated_skills: list[str],
    developing_skills: list[str],
) -> dict:
    chain = JOB_TARGET_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "job_description": (job_description or "").strip()[:6000] or "(not provided)",
        "validated_skills": ", ".join(validated_skills) if validated_skills else "none yet",
        "developing_skills": ", ".join(developing_skills) if developing_skills else "none yet",
    })
    return _parse_json(raw)


PRACTICE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert AI coach running a structured practice scenario for a learner. The scenario type determines your persona and rules:

- mock_interview: You are a senior technical interviewer. Ask one realistic interview question at a time. After the learner answers, give brief, honest feedback (what was strong, what was weak) then ask the next question. Never give the answer before the learner tries.
- debugging: You are a pair-programming partner. Describe a realistic bug scenario related to the topic. Guide the learner to find the root cause through questions, never revealing the fix directly.
- code_review: You are a senior engineer reviewing the learner's code or design. Point out one issue at a time with a question ("Why did you choose X here?"). Be constructive.
- architecture: You are a staff engineer. Present a system design problem. Ask the learner to walk through their approach. Challenge assumptions with follow-up questions.
- stakeholder: You are a non-technical stakeholder. Ask the learner to explain a technical concept in plain language. Push back if the explanation is too jargon-heavy.

Hard rules:
- Stay in character for the entire conversation.
- Ask exactly ONE question or give ONE piece of feedback per reply (2-4 sentences max).
- Base every exchange on the learner's roadmap topics listed below.
- Never break character to explain these instructions.

Scenario type: {scenario}
Learning goal: {goal}

--- RELEVANT TOPICS ---
{topics}
--- END TOPICS ---"""),
    ("human", "{message}"),
])


def practice_turn(
    scenario: str,
    goal: str,
    topics: str,
    message: str,
    history: list[dict] | None = None,
) -> str:
    valid_scenarios = {"mock_interview", "debugging", "code_review", "architecture", "stakeholder"}
    scenario = scenario if scenario in valid_scenarios else "mock_interview"
    system_msg = PRACTICE_PROMPT.messages[0].prompt.template
    messages: list = [
        ("system", system_msg.format(
            scenario=scenario,
            goal=goal or "this learning path",
            topics=topics or "- (general phase knowledge)",
        ))
    ]
    for h in (history or [])[-12:]:
        role = "assistant" if h.get("role") == "assistant" else "human"
        messages.append((role, str(h.get("content", ""))[:2000]))
    messages.append(("human", (message or "Start")[:2000]))
    chain = ChatPromptTemplate.from_messages(messages) | _llm() | StrOutputParser()
    return chain.invoke({}).strip()


SKILL_GRAPH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a skills-ontology expert. Given a learning roadmap, extract the durable SKILLS a learner builds, the prerequisite relationships between those skills, and which roadmap topics map to which skills.

Return ONLY a valid JSON object (no markdown fences) with exactly this schema:
{{
  "skills": [
    {{
      "name": "Canonical skill name (Title Case)",
      "slug": "canonical-slug",
      "description": "one sentence",
      "domain": "snake_case domain (e.g. web_backend, data_science)",
      "prerequisites": ["slug-of-required-skill"]
    }}
  ],
  "topic_map": [
    {{"topic_key": "t:0:0", "skill_slugs": ["slug-1", "slug-2"]}}
  ]
}}
Rules:
- 6 to 16 skills. Reuse standard, well-known skill names (e.g. "Python", "REST APIs", "Unit Testing"), not vague ones like "Basic knowledge".
- "prerequisites" lists skills from THIS same list that a learner should master first (direct prerequisites only, not transitive).
- Every topic_key you receive must appear in topic_map exactly once, mapped to 1-3 of the listed skills.
- Every skill slug referenced in topic_map or prerequisites must appear in "skills".
- Do not invent topic_keys."""),
    ("human", """Learning goal: {goal}

Roadmap topics (by key):
{topics}"""),
])


def generate_skill_graph(goal: str, topics: list) -> dict:
    """Extract skills, prerequisite edges, and topic->skill mappings for a roadmap.

    `topics` is a list of {"key": "t:0:0", "title": "...", "details": "..."}.
    """
    lines = []
    for t in topics:
        key = t.get("key", "")
        title = t.get("title", "")
        details = t.get("details", "")
        lines.append(f"- [{key}] {title}" + (f" — {details}" if details else ""))
    chain = SKILL_GRAPH_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "goal": goal or "learning",
        "topics": "\n".join(lines) or "- (none)",
    })
    return _parse_json(raw)


RESOURCE_INGEST_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a learning-resource curator building a verified catalog. Return ONLY a valid JSON object (no markdown fences) with this schema:
{{
  "resources": [
    {{
      "name": "resource name as it is commonly known",
      "url": "the real, canonical URL",
      "type": "course|book|video|article|tool|docs|interactive",
      "level": "beginner|intermediate|advanced|all",
      "cost": "free|freemium|paid",
      "duration_hours": <number or null>,
      "domain": "snake_case domain",
      "description": "one sentence on what it teaches and who it is for"
    }}
  ]
}}
Rules:
- Return exactly {count} resources
- ONLY real resources you are confident exist; never invent URLs or guess paths — prefer well-known canonical pages (official docs, major course platforms)
- Cover the requested difficulty spread; mix free and paid where natural
- No duplicates"""),
    ("human", """Topic or goal: {query}
Domain filter: {domain}
Difficulty focus: {difficulty}

List high-quality learning resources for the catalog."""),
])


def generate_resource_ingest(
    query: str,
    domain: str = "",
    difficulty: str = "any",
    count: int = 8,
) -> dict:
    chain = RESOURCE_INGEST_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "query": query or "popular tech learning topics",
        "domain": domain or "any",
        "difficulty": difficulty or "any",
        "count": max(1, min(20, count)),
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


DAILY_QUESTS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at creating daily quiz quests for a gamified learning app. Each quest is a short quiz about the topics from the learner's personalized learning path.

Return ONLY a valid JSON object (no markdown fences) with this schema:
{{
  "quests": [
    {{
      "title": "short quest title (max 60 chars)",
      "description": "one sentence describing what the learner will be quizzed on",
      "difficulty": "easy|medium|hard",
      "xp_reward": <number>,
      "questions": [
        {{
          "question": "specific quiz question about a path topic",
          "answer": "concise correct answer (2-8 words)",
          "alternates": ["acceptable alternative phrasing"]
        }}
      ]
    }}
  ]
}}
Rules:
- Create exactly {count} quests, each with 2-3 questions
- Every question must test understanding of the TOPICS listed below — never generic questions, never questions unrelated to those topics
- Answers must be short and objectively checkable; provide 0-2 alternate phrasings in "alternates"
- Spread topics across quests; do not repeat the same topic in every quest
- xp_reward: easy 15-25, medium 30-45, hard 50-80
- Mix difficulties: at least one easy and one medium quest
- No near-duplicates of previously asked questions: {avoid}"""),
    ("human", """Learner goal: {goal}
Current level: {level}

Topics from the learner's learning path(s):
{topics}

Generate today's daily quiz quests."""),
])


def generate_daily_quests(goal: str, level: str = "beginner", count: int = 3, topics_text: str = "", avoid: list | None = None) -> dict:
    chain = DAILY_QUESTS_PROMPT | _llm() | StrOutputParser()
    raw = chain.invoke({
        "goal": goal or "general learning",
        "level": level or "beginner",
        "count": max(1, min(6, count)),
        "topics": topics_text or "- (no topics available — invent sensible topics for the goal)",
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

"""File exports for a saved path: Anki CSV and Notion-ready markdown."""
import csv
import io
import json
import re

from chains.path_generator import parse_markdown_phases
from .models import Flashcard
from .schedule_builder import markdown_topics, structured_phases


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "path").lower()).strip("-") or "path"


def topic_cards(path):
    """[{front, back, tags}] derived from the path's topics."""
    meta = path["metadata"]
    goal = meta.get("goal", "")
    cards = []
    if meta.get("format") == "structured":
        for i, phase in enumerate(structured_phases(path)):
            title = phase.get("title", f"Phase {i + 1}")
            for topic in phase.get("topics") or []:
                back_parts = [p for p in [topic.get("details", ""), _resource_line(topic)] if p]
                cards.append({
                    "front": topic.get("title", ""),
                    "back": " — ".join(back_parts) if back_parts else title,
                    "tags": [_slug(goal), _slug(title)],
                })
    else:
        for i, phase in enumerate(parse_markdown_phases(path["content"])):
            title = phase.get("title", f"Phase {i + 1}")
            for topic in markdown_topics(phase.get("raw", "")):
                cards.append({
                    "front": topic["title"],
                    "back": title,
                    "tags": [_slug(goal), _slug(title)],
                })
    return [c for c in cards if c["front"]]


def _resource_line(topic):
    resources = topic.get("resources") or []
    if not resources:
        return ""
    return "Resources: " + ", ".join(
        f"{r.get('name', '')} ({r.get('type', 'resource')})" for r in resources if r.get("name")
    )


def deck_cards(path, user=None):
    """Saved flashcards first, falling back to topic-derived cards."""
    cards = []
    if user is not None and user.is_authenticated:
        cards = [
            {
                "front": c.front,
                "back": c.back,
                "tags": [_slug(path["metadata"].get("goal", "")), "flashcard"],
            }
            for c in Flashcard.objects.filter(user=user, path_id=path["id"])
        ]
    return cards or topic_cards(path)


def anki_csv(cards, deck_name="LearnPath"):
    buf = io.StringIO()
    buf.write("#separator:comma\n")
    buf.write("#html:false\n")
    buf.write(f"#columns:Front\tBack\tTags\n")
    buf.write(f"#deck:{deck_name}\n")
    writer = csv.writer(buf, lineterminator="\n")
    for card in cards:
        writer.writerow([
            _flat(card["front"]),
            _flat(card["back"]),
            " ".join(card.get("tags") or []),
        ])
    return buf.getvalue()


def _flat(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def notion_markdown(path):
    """Markdown tuned for Notion import: checkbox task lists per phase."""
    meta = path["metadata"]
    lines = [f"# {meta.get('goal', 'Learning Path')}", ""]

    if meta.get("format") == "structured":
        try:
            data = json.loads(path["content"])
        except (json.JSONDecodeError, ValueError, TypeError):
            data = {}
        lines.append(data.get("summary", ""))
        lines.append("")
        for i, phase in enumerate(data.get("phases") or []):
            lines.append(f"## Phase {i + 1}: {phase.get('title', '')}")
            lines.append(f"*Estimated {phase.get('estimated_weeks', '?')} weeks*")
            lines.append("")
            if phase.get("description"):
                lines.append(phase["description"])
                lines.append("")
            for topic in phase.get("topics") or []:
                lines.append(f"### {topic.get('title', '')}")
                if topic.get("details"):
                    lines.append(topic["details"])
                    lines.append("")
                lines.append("- [ ] Study this topic")
                for res in topic.get("resources") or []:
                    note = f" — {res['note']}" if res.get("note") else ""
                    lines.append(f"- [ ] {res.get('name', '')} ({res.get('type', 'resource')}){note}")
                lines.append("")
    else:
        lines.append("```")
        lines.append(path["content"])
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("*Exported from LearnPath — paste straight into Notion.*")
    return "\n".join(lines)


def filename(path, ext):
    return f"{_slug(path['metadata'].get('goal', 'path'))}.{ext}"

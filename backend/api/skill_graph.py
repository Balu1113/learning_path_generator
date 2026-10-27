"""Skill graph + mastery: persistence and evidence rules.

Mastery states: unassessed (no SkillMastery row) -> developing (any evidence)
-> validated (strong evidence: passed phase test >= threshold, or reviewed project
score >= threshold). We keep the best score and never downgrade.
"""
import re
from datetime import datetime, timezone

from django.db.models import Max

from .models import PathSkill, Skill, SkillEdge, SkillMastery

VALIDATE_THRESHOLD = 70
MAX_SKILLS_PER_TOPIC = 3


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug[:140] or "skill"


def upsert_skill(name: str, description: str = "", domain: str = "", slug: str | None = None) -> Skill:
    name = (name or "").strip()[:120]
    slug = _slugify(slug or name)
    skill = Skill.objects.filter(slug=slug).first()
    if skill is None:
        skill = Skill.objects.create(
            name=name or slug.title(),
            slug=slug,
            description=(description or "").strip(),
            domain=(domain or "").strip()[:80],
        )
    else:
        updates = {}
        if description and not skill.description:
            updates["description"] = description.strip()
        if domain and not skill.domain:
            updates["domain"] = domain.strip()[:80]
        if updates:
            for key, value in updates.items():
                setattr(skill, key, value
                )
            skill.save(update_fields=list(updates))
    return skill


def _valid_slug(slug, known: dict) -> Skill | None:
    if not isinstance(slug, str):
        return None
    return known.get(_slugify(slug))


def apply_skill_graph(user, path_id: str, graph: dict, topic_titles: dict | None = None) -> dict:
    """Persist skills, prerequisite edges, and topic mappings from an LLM graph.

    Returns {"skills": [...], "edges": [[from, to], ...], "topics_mapped": int}.
    Existing topic mappings for this path are replaced.
    """
    raw_skills = graph.get("skills") or []
    known: dict[str, Skill] = {}
    ordered: list[Skill] = []
    for entry in raw_skills:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        skill = upsert_skill(
            name=name,
            description=str(entry.get("description") or ""),
            domain=str(entry.get("domain") or ""),
            slug=str(entry.get("slug") or "") or None,
        )
        if skill.slug not in known:
            known[skill.slug] = skill
            ordered.append(skill)

    edges = []
    for entry in raw_skills:
        if not isinstance(entry, dict):
            continue
        from_skill = _valid_slug(entry.get("slug") or entry.get("name"), known)
        if from_skill is None:
            continue
        for pre in entry.get("prerequisites") or []:
            to_skill = _valid_slug(pre, known)
            if to_skill is None or to_skill.id == from_skill.id:
                continue
            # Edge direction: prerequisite -> dependent (from unlocks to).
            _, created = SkillEdge.objects.get_or_create(from_skill=to_skill, to_skill=from_skill)
            if created:
                edges.append([to_skill.slug, from_skill.slug])

    PathSkill.objects.filter(user=user, path_id=path_id).delete()
    topics_mapped = 0
    for entry in graph.get("topic_map") or []:
        if not isinstance(entry, dict):
            continue
        topic_key = str(entry.get("topic_key") or "").strip()
        if not topic_key:
            continue
        topic_title = ""
        if isinstance(topic_titles, dict):
            topic_title = str(topic_titles.get(topic_key) or "")[:255]
        slugs = entry.get("skill_slugs") or []
        linked = 0
        for slug in slugs:
            skill = _valid_slug(slug, known)
            if skill is None or linked >= MAX_SKILLS_PER_TOPIC:
                continue
            PathSkill.objects.create(
                user=user,
                path_id=path_id,
                topic_key=topic_key,
                topic_title=topic_title,
                phase_idx=_phase_from_key(topic_key),
                skill=skill,
            )
            linked += 1
        if linked:
            topics_mapped += 1

    return {
        "skills": [
            {
                "name": s.name,
                "slug": s.slug,
                "description": s.description,
                "domain": s.domain,
            }
            for s in ordered
        ],
        "edges": edges,
        "topics_mapped": topics_mapped,
    }


def _phase_from_key(topic_key: str) -> int:
    # topic keys look like "t:<phase>:<topic>"
    parts = (topic_key or "").split(":")
    if len(parts) >= 2 and parts[0] == "t":
        try:
            return max(0, int(parts[1]))
        except ValueError:
            pass
    return 0


def record_skill_evidence(user, path_id: str, phase_idx: int, score: int, strong: bool) -> list:
    """Update mastery for every skill mapped to this phase's topics.

    Any evidence marks the skill developing; strong evidence (score >= threshold)
    validates it. Best score is kept; mastery never downgrades.
    """
    if user is None or not user.is_authenticated:
        return []
    now = datetime.now(tz=timezone.utc)
    skill_ids = set(
        PathSkill.objects.filter(user=user, path_id=path_id, phase_idx=phase_idx)
        .values_list("skill_id", flat=True)
    )
    updated = []
    for skill_id in skill_ids:
        row, created = SkillMastery.objects.get_or_create(
            user=user, skill_id=skill_id,
            defaults={
                "state": SkillMastery.STATE_VALIDATED if (strong and score >= VALIDATE_THRESHOLD) else SkillMastery.STATE_DEVELOPING,
                "score": max(0, min(100, score)),
                "evidence_count": 1,
                "last_evidence_at": now,
            },
        )
        if created:
            updated.append(row)
            continue
        changes = {"evidence_count": row.evidence_count + 1, "last_evidence_at": now}
        if score > row.score:
            changes["score"] = max(0, min(100, score))
        if strong and score >= VALIDATE_THRESHOLD and row.state != SkillMastery.STATE_VALIDATED:
            changes["state"] = SkillMastery.STATE_VALIDATED
        if changes:
            for key, value in changes.items():
                setattr(row, key, value)
            row.save(update_fields=list(changes) + ["updated_at"])
            updated.append(row)
    return updated


def mastery_map(user) -> dict:
    """slug -> mastery row (or None) for quick lookups."""
    if user is None or not user.is_authenticated:
        return {}
    return {
        m.skill.slug: m
        for m in SkillMastery.objects.filter(user=user).select_related("skill")
    }


def topic_skill_states(user, path_id: str) -> dict:
    """topic_key -> {"validated": n, "total": n, "all_validated": bool}."""
    rows = PathSkill.objects.filter(user=user, path_id=path_id).select_related("skill")
    mastery = mastery_map(user)
    per_topic: dict[str, dict] = {}
    for row in rows:
        entry = per_topic.setdefault(row.topic_key, {"validated": 0, "total": 0})
        entry["total"] += 1
        m = mastery.get(row.skill.slug)
        if m is not None and m.state == SkillMastery.STATE_VALIDATED:
            entry["validated"] += 1
    for entry in per_topic.values():
        entry["all_validated"] = entry["total"] > 0 and entry["validated"] == entry["total"]
    return per_topic


def path_skill_matrix(user, path_id: str) -> dict:
    """Full mastery matrix for one path: skills, their states, and prerequisite edges."""
    mappings = (
        PathSkill.objects.filter(user=user, path_id=path_id)
        .select_related("skill")
        .order_by("phase_idx", "topic_key")
    )
    mastery = mastery_map(user)
    skills: dict[str, dict] = {}
    topic_keys: dict[str, list] = {}
    for row in mappings:
        slug = row.skill.slug
        entry = skills.get(slug)
        if entry is None:
            m = mastery.get(slug)
            entry = {
                "name": row.skill.name,
                "slug": slug,
                "description": row.skill.description,
                "domain": row.skill.domain,
                "state": "validated" if (m and m.state == SkillMastery.STATE_VALIDATED) else
                         ("developing" if m else "unassessed"),
                "score": m.score if m else None,
                "evidence_count": m.evidence_count if m else 0,
                "last_evidence_at": m.last_evidence_at.isoformat() if (m and m.last_evidence_at) else None,
                "topic_keys": [],
            }
            skills[slug] = entry
        entry["topic_keys"].append(row.topic_key)
        topic_keys.setdefault(row.topic_key, []).append(slug)

    slugs = set(skills)
    edges = [
        {"from": e.from_skill.slug, "to": e.to_skill.slug}
        for e in SkillEdge.objects.filter(from_skill__slug__in=slugs, to_skill__slug__in=slugs)
    ]
    skill_list = sorted(skills.values(), key=lambda s: (s["state"] != "validated", s["state"] != "developing", s["name"]))
    counts = {"unassessed": 0, "developing": 0, "validated": 0}
    for s in skill_list:
        counts[s["state"]] += 1
    return {"skills": skill_list, "edges": edges, "topic_map": topic_keys, "counts": counts}


def best_scores_by_phase(user, path_id: str) -> dict[int, int]:
    """Best phase-test percentage per phase (used for re-assessment decisions)."""
    from .models import TestResult
    rows = (
        TestResult.objects.filter(user=user, path_id=path_id)
        .values("phase_idx")
        .annotate(best=Max("percent"))
    )
    return {r["phase_idx"]: r["best"] for r in rows}

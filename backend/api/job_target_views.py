import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
from .models import Skill, SkillMastery, PathSkill
from .views import _json_body

load_dotenv()


@csrf_protect
@require_POST
def analyze_job_description(request):
    """Analyze job description to extract required skills."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    data = _json_body(request)
    job_description = data.get('job_description', '').strip()
    job_title = data.get('job_title', 'Unknown Position')

    if not job_description:
        return JsonResponse({'error': 'Job description required'}, status=400)

    if len(job_description) > 5000:
        return JsonResponse({'error': 'Job description too long'}, status=400)

    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        prompt = f"""Analyze this job description and extract required skills.

Job Title: {job_title}

Job Description:
{job_description}

Extract and categorize skills into:
1. Technical Skills (programming languages, frameworks, tools)
2. Domain Skills (industry-specific knowledge)
3. Soft Skills (communication, leadership, etc.)
4. Certifications (if mentioned)

For each skill, estimate the proficiency level needed (beginner, intermediate, advanced, expert).

Return as JSON with this structure:
{{
  "technical_skills": [
    {{"name": "Python", "level": "intermediate", "importance": "high"}},
    ...
  ],
  "domain_skills": [...],
  "soft_skills": [...],
  "certifications": [...],
  "summary": "Brief summary of role requirements"
}}

Return ONLY valid JSON, no other text."""

        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        try:
            skills_data = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                skills_data = json.loads(response_text[start:end])
            else:
                return JsonResponse({'error': 'Failed to parse skills'}, status=500)

        return JsonResponse({
            'job_title': job_title,
            'skills': skills_data,
        })

    except Exception as e:
        return JsonResponse({'error': f'Analysis failed: {str(e)}'}, status=500)


@require_POST
def find_skill_gaps(request):
    """Find skill gaps between user's current skills and job requirements."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    data = _json_body(request)
    required_skills = data.get('required_skills', [])

    if not required_skills:
        return JsonResponse({'error': 'Required skills list needed'}, status=400)

    user_mastery = SkillMastery.objects.filter(user=request.user).select_related('skill')
    user_skills = {m.skill.name.lower(): m.state for m in user_mastery}

    gaps = []
    matched = []

    for skill_data in required_skills:
        skill_name = skill_data.get('name', '').lower()
        required_level = skill_data.get('level', 'intermediate')
        importance = skill_data.get('importance', 'medium')

        if skill_name in user_skills:
            user_level = user_skills[skill_name]
            matched.append({
                'skill': skill_data.get('name'),
                'user_level': user_level,
                'required_level': required_level,
                'gap': _calculate_gap(user_level, required_level),
            })
        else:
            gaps.append({
                'skill': skill_data.get('name'),
                'required_level': required_level,
                'importance': importance,
                'user_level': 'unassessed',
            })

    gap_score = (len(gaps) / max(1, len(required_skills))) * 100

    return JsonResponse({
        'total_skills_required': len(required_skills),
        'skills_matched': len(matched),
        'skill_gaps': len(gaps),
        'gap_score': round(gap_score, 1),
        'gaps': gaps,
        'matched_skills': matched,
        'recommendation': _get_recommendation(gap_score, len(gaps)),
    })


@require_GET
def job_target_paths(request):
    """Get recommended learning paths for job target."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    job_title = request.GET.get('job_title', '')
    skill_gaps = request.GET.getlist('gaps', [])

    if not job_title:
        return JsonResponse({'error': 'Job title required'}, status=400)

    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        prompt = f"""Create a learning path for someone targeting this job:

Job Title: {job_title}
Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'General preparation'}

Design a structured learning path with:
1. Phase 1: Foundation skills
2. Phase 2: Core technical skills
3. Phase 3: Advanced topics
4. Phase 4: Project-based learning
5. Phase 5: Interview preparation

For each phase, include:
- Duration (weeks)
- Key topics
- Learning resources (types)
- Projects/exercises
- Assessment methods

Return as JSON with this structure:
{{
  "job_title": "{job_title}",
  "total_duration_weeks": 12,
  "phases": [
    {{
      "phase": 1,
      "title": "Foundation",
      "duration_weeks": 2,
      "topics": ["Topic 1", "Topic 2"],
      "resources": ["Videos", "Articles"],
      "projects": ["Project description"],
      "assessment": "Quiz"
    }},
    ...
  ],
  "success_criteria": "What success looks like"
}}

Return ONLY valid JSON."""

        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        try:
            path_data = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                path_data = json.loads(response_text[start:end])
            else:
                return JsonResponse({'error': 'Failed to parse path'}, status=500)

        return JsonResponse(path_data)

    except Exception as e:
        return JsonResponse({'error': f'Path generation failed: {str(e)}'}, status=500)


@require_GET
def job_market_insights(request):
    """Get market insights for a job title."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    job_title = request.GET.get('job_title', '')

    if not job_title:
        return JsonResponse({'error': 'Job title required'}, status=400)

    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        prompt = f"""Provide market insights for the "{job_title}" position.

Include:
1. Average salary range
2. Job market demand (high/medium/low)
3. Top companies hiring
4. Key skills in demand
5. Career growth opportunities
6. Common interview questions
7. Certifications that help
8. Industry trends

Return as JSON with this structure:
{{
  "job_title": "{job_title}",
  "salary_range": {{"min": 80000, "max": 150000, "currency": "USD"}},
  "market_demand": "high",
  "top_companies": ["Company 1", "Company 2"],
  "key_skills": ["Skill 1", "Skill 2"],
  "growth_opportunities": "Description",
  "common_questions": ["Question 1", "Question 2"],
  "helpful_certifications": ["Cert 1"],
  "industry_trends": "Current trends"
}}

Return ONLY valid JSON."""

        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        try:
            insights = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                insights = json.loads(response_text[start:end])
            else:
                return JsonResponse({'error': 'Failed to parse insights'}, status=500)

        return JsonResponse(insights)

    except Exception as e:
        return JsonResponse({'error': f'Insights generation failed: {str(e)}'}, status=500)


def _calculate_gap(user_level, required_level):
    """Calculate skill gap between user level and required level."""
    levels = {'unassessed': 0, 'developing': 1, 'validated': 2}
    user_score = levels.get(user_level, 0)
    required_score = levels.get(required_level, 1)
    return max(0, required_score - user_score)


def _get_recommendation(gap_score, gap_count):
    """Get recommendation based on gap score."""
    if gap_score < 20:
        return f"Great! You're well-prepared. Focus on {gap_count} remaining skill(s)."
    elif gap_score < 50:
        return f"Good foundation. You need to develop {gap_count} key skill(s)."
    elif gap_score < 80:
        return f"Significant gaps. Consider a structured learning path for {gap_count} skill(s)."
    else:
        return f"Major gaps. Recommend comprehensive training for {gap_count} skill(s)."

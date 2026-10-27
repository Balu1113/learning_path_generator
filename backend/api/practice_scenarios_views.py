import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
from .models import ConversationHistory
from .views import _json_body

load_dotenv()


@require_GET
def practice_scenarios_list(request, doc_id, phase_idx):
    """Get available practice scenarios for a phase."""
    scenarios = [
        {
            'id': 'mock_interview',
            'title': 'Mock Interview',
            'description': 'Practice answering technical interview questions',
            'difficulty': 'medium',
            'duration_minutes': 30,
            'icon': '🎤',
        },
        {
            'id': 'code_review',
            'title': 'Code Review',
            'description': 'Review code and provide feedback',
            'difficulty': 'medium',
            'duration_minutes': 20,
            'icon': '👀',
        },
        {
            'id': 'debugging',
            'title': 'Debugging Challenge',
            'description': 'Find and fix bugs in code',
            'difficulty': 'hard',
            'duration_minutes': 25,
            'icon': '🐛',
        },
        {
            'id': 'system_design',
            'title': 'System Design',
            'description': 'Design a system architecture',
            'difficulty': 'hard',
            'duration_minutes': 45,
            'icon': '🏗️',
        },
        {
            'id': 'problem_solving',
            'title': 'Problem Solving',
            'description': 'Solve algorithmic problems',
            'difficulty': 'medium',
            'duration_minutes': 30,
            'icon': '🧩',
        },
    ]

    return JsonResponse({'scenarios': scenarios})


@csrf_protect
@require_POST
def start_practice_scenario(request, doc_id, phase_idx):
    """Start a practice scenario session."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    data = _json_body(request)
    scenario_type = data.get('scenario_type', 'mock_interview')
    topic = data.get('topic', 'General')

    conversation, created = ConversationHistory.objects.get_or_create(
        user=request.user,
        topic=f"{scenario_type}_{topic}",
        defaults={'messages': []}
    )

    initial_prompt = _get_scenario_prompt(scenario_type, topic)

    return JsonResponse({
        'conversation_id': conversation.id,
        'scenario_type': scenario_type,
        'topic': topic,
        'initial_prompt': initial_prompt,
    })


@csrf_protect
@require_POST
def submit_practice_response(request, conversation_id):
    """Submit response to practice scenario."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        conversation = ConversationHistory.objects.get(id=conversation_id, user=request.user)
    except ConversationHistory.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

    data = _json_body(request)
    user_response = data.get('response', '').strip()

    if not user_response:
        return JsonResponse({'error': 'Response required'}, status=400)

    if len(user_response) > 5000:
        return JsonResponse({'error': 'Response too long'}, status=400)

    conversation.messages.append({
        'role': 'user',
        'content': user_response,
        'timestamp': timezone.now().isoformat(),
    })

    ai_feedback = _generate_practice_feedback(conversation.topic, conversation.messages)
    score = _calculate_practice_score(user_response, conversation.topic)

    conversation.messages.append({
        'role': 'assistant',
        'content': ai_feedback,
        'timestamp': timezone.now().isoformat(),
    })

    conversation.updated_at = timezone.now()
    conversation.save()

    return JsonResponse({
        'feedback': ai_feedback,
        'score': score,
        'messages': conversation.messages[-2:],
    })


@require_GET
def practice_history(request, doc_id):
    """Get user's practice scenario history."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    conversations = ConversationHistory.objects.filter(
        user=request.user,
        topic__startswith='mock_interview'
    ).order_by('-updated_at')[:20]

    return JsonResponse({
        'sessions': [
            {
                'id': c.id,
                'topic': c.topic.replace('mock_interview_', ''),
                'message_count': len(c.messages),
                'last_message': c.messages[-1]['content'][:100] if c.messages else '',
                'updated_at': c.updated_at.isoformat(),
            }
            for c in conversations
        ]
    })


@require_GET
def practice_tips(request):
    """Get tips for practice scenarios."""
    tips = {
        'mock_interview': [
            'Think out loud - explain your reasoning',
            'Ask clarifying questions',
            'Provide concrete examples',
            'Discuss trade-offs and alternatives',
            'Show your problem-solving process',
        ],
        'code_review': [
            'Look for code quality issues',
            'Check for performance problems',
            'Verify error handling',
            'Suggest improvements',
            'Provide constructive feedback',
        ],
        'debugging': [
            'Understand the expected behavior',
            'Reproduce the bug',
            'Isolate the problem',
            'Test your fix',
            'Prevent similar bugs',
        ],
        'system_design': [
            'Clarify requirements',
            'Discuss trade-offs',
            'Design for scalability',
            'Consider failure modes',
            'Estimate resource usage',
        ],
        'problem_solving': [
            'Understand the problem',
            'Think of edge cases',
            'Optimize your solution',
            'Explain your approach',
            'Test with examples',
        ],
    }

    return JsonResponse({'tips': tips})


def _get_scenario_prompt(scenario_type, topic):
    """Get initial prompt for scenario type."""
    prompts = {
        'mock_interview': f"Let's do a mock interview about {topic}. I'll ask you technical questions. Ready?",
        'code_review': f"I'll show you some code related to {topic}. Please review it and provide feedback.",
        'debugging': f"Here's a buggy code snippet about {topic}. Can you find and fix the bugs?",
        'system_design': f"Design a system for {topic}. Let's discuss the architecture.",
        'problem_solving': f"Let's solve a problem about {topic}. I'll give you the problem statement.",
    }
    return prompts.get(scenario_type, "Let's practice!")


def _generate_practice_feedback(topic, messages):
    """Generate AI feedback on practice response."""
    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        scenario_type = topic.split('_')[0] if '_' in topic else 'general'

        prompt = f"""You are an expert interviewer/reviewer evaluating a candidate's response.

Scenario: {scenario_type}
Topic: {topic}

Evaluate the response on:
1. Technical accuracy
2. Clarity of explanation
3. Problem-solving approach
4. Communication skills
5. Depth of understanding

Provide:
- Strengths (what they did well)
- Areas for improvement
- Specific suggestions
- Follow-up question or next challenge

Keep feedback constructive and encouraging."""

        response = llm.invoke([HumanMessage(content=prompt)])
        feedback = response.content if isinstance(response.content, str) else str(response.content)
        return feedback.strip()
    except Exception as e:
        return f"Feedback generation failed: {str(e)}"


def _calculate_practice_score(response, topic):
    """Calculate score for practice response."""
    score = 50

    if len(response) > 200:
        score += 15
    if len(response) > 500:
        score += 15
    if '.' in response:
        score += 10
    if len(response.split()) > 50:
        score += 10

    return min(100, score)


@require_GET
def interview_questions(request):
    """Get common interview questions for a topic."""
    topic = request.GET.get('topic', 'General')

    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        prompt = f"""Generate 5 common interview questions for someone with {topic} experience.

For each question, provide:
1. The question
2. What the interviewer is looking for
3. Tips for answering
4. Example answer structure

Return as JSON:
{{
  "topic": "{topic}",
  "questions": [
    {{
      "question": "Question text",
      "what_they_want": "What interviewer is looking for",
      "tips": ["Tip 1", "Tip 2"],
      "example_structure": "How to structure your answer"
    }},
    ...
  ]
}}

Return ONLY valid JSON."""

        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        try:
            questions = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                questions = json.loads(response_text[start:end])
            else:
                return JsonResponse({'error': 'Failed to parse questions'}, status=500)

        return JsonResponse(questions)

    except Exception as e:
        return JsonResponse({'error': f'Question generation failed: {str(e)}'}, status=500)


@require_GET
def coding_challenges(request):
    """Get coding challenges for practice."""
    difficulty = request.GET.get('difficulty', 'medium')
    topic = request.GET.get('topic', 'General')

    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        prompt = f"""Generate 3 coding challenges for {difficulty} level about {topic}.

For each challenge, provide:
1. Problem statement
2. Input/output examples
3. Constraints
4. Hints
5. Solution approach

Return as JSON:
{{
  "challenges": [
    {{
      "title": "Challenge title",
      "description": "Problem statement",
      "examples": [
        {{"input": "...", "output": "..."}}
      ],
      "constraints": ["Constraint 1"],
      "hints": ["Hint 1"],
      "solution_approach": "How to solve it"
    }},
    ...
  ]
}}

Return ONLY valid JSON."""

        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        try:
            challenges = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                challenges = json.loads(response_text[start:end])
            else:
                return JsonResponse({'error': 'Failed to parse challenges'}, status=500)

        return JsonResponse(challenges)

    except Exception as e:
        return JsonResponse({'error': f'Challenge generation failed: {str(e)}'}, status=500)

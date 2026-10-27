import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
from .models import VoicePracticeSession, ConversationHistory
from .views import _json_body

load_dotenv()


@require_GET
def practice_scenarios(request, doc_id, phase_idx):
    """Get available practice scenarios for a phase."""
    scenarios = [
        {
            'id': 'mock_interview',
            'title': 'Mock Interview',
            'description': 'Practice answering technical interview questions',
            'difficulty': 'medium',
        },
        {
            'id': 'pronunciation',
            'title': 'Pronunciation Practice',
            'description': 'Practice pronouncing technical terms',
            'difficulty': 'easy',
        },
        {
            'id': 'explanation',
            'title': 'Concept Explanation',
            'description': 'Explain concepts in your own words',
            'difficulty': 'medium',
        },
        {
            'id': 'debate',
            'title': 'Technical Debate',
            'description': 'Debate technical approaches and trade-offs',
            'difficulty': 'hard',
        },
    ]
    
    return JsonResponse({'scenarios': scenarios})


@csrf_protect
@require_POST
def start_voice_session(request, doc_id, phase_idx):
    """Start a new voice practice session."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    data = _json_body(request)
    scenario_type = data.get('scenario_type', 'mock_interview')
    topic = data.get('topic', 'General')

    session = VoicePracticeSession.objects.create(
        user=request.user,
        path_id=doc_id,
        phase_idx=phase_idx,
        scenario_type=scenario_type,
        topic=topic,
    )

    initial_prompt = _get_scenario_prompt(scenario_type, topic)

    return JsonResponse({
        'session_id': session.id,
        'scenario_type': scenario_type,
        'topic': topic,
        'initial_prompt': initial_prompt,
    })


@csrf_protect
@require_POST
def submit_voice_response(request, session_id):
    """Submit voice response and get AI feedback."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        session = VoicePracticeSession.objects.get(id=session_id, user=request.user)
    except VoicePracticeSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    data = _json_body(request)
    transcript = data.get('transcript', '').strip()

    if not transcript:
        return JsonResponse({'error': 'Transcript required'}, status=400)

    session.transcript = transcript
    session.save()

    feedback = _generate_ai_feedback(session.scenario_type, session.topic, transcript)
    score = _calculate_score(transcript, session.scenario_type)

    session.ai_feedback = feedback
    session.score = score
    session.save()

    return JsonResponse({
        'feedback': feedback,
        'score': score,
        'transcript': transcript,
    })


@require_GET
def session_history(request, doc_id):
    """Get user's voice practice session history."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    sessions = VoicePracticeSession.objects.filter(
        user=request.user,
        path_id=doc_id
    ).order_by('-created_at')[:20]

    return JsonResponse({
        'sessions': [
            {
                'id': s.id,
                'scenario_type': s.scenario_type,
                'topic': s.topic,
                'score': s.score,
                'transcript': s.transcript[:100] if s.transcript else '',
                'created_at': s.created_at.isoformat(),
            }
            for s in sessions
        ]
    })


@require_GET
def tutor_chat(request):
    """Get AI tutor chat interface."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    topic = request.GET.get('topic', 'General Learning')
    
    conversation, created = ConversationHistory.objects.get_or_create(
        user=request.user,
        topic=topic,
        defaults={'messages': []}
    )

    return JsonResponse({
        'conversation_id': conversation.id,
        'topic': conversation.topic,
        'messages': conversation.messages,
    })


@csrf_protect
@require_POST
def tutor_message(request, conversation_id):
    """Send message to AI tutor."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        conversation = ConversationHistory.objects.get(id=conversation_id, user=request.user)
    except ConversationHistory.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

    data = _json_body(request)
    user_message = data.get('message', '').strip()

    if not user_message:
        return JsonResponse({'error': 'Message required'}, status=400)

    if len(user_message) > 2000:
        return JsonResponse({'error': 'Message too long'}, status=400)

    conversation.messages.append({
        'role': 'user',
        'content': user_message,
        'timestamp': timezone.now().isoformat(),
    })

    ai_response = _get_tutor_response(conversation.topic, conversation.messages)

    conversation.messages.append({
        'role': 'assistant',
        'content': ai_response,
        'timestamp': timezone.now().isoformat(),
    })

    conversation.updated_at = timezone.now()
    conversation.save()

    return JsonResponse({
        'response': ai_response,
        'messages': conversation.messages[-2:],
    })


@require_GET
def my_conversations(request):
    """Get user's tutor conversations."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    conversations = ConversationHistory.objects.filter(user=request.user).order_by('-updated_at')[:20]

    return JsonResponse({
        'conversations': [
            {
                'id': c.id,
                'topic': c.topic,
                'message_count': len(c.messages),
                'last_message': c.messages[-1]['content'][:100] if c.messages else '',
                'updated_at': c.updated_at.isoformat(),
            }
            for c in conversations
        ]
    })


def _get_scenario_prompt(scenario_type, topic):
    """Get initial prompt for scenario type."""
    prompts = {
        'mock_interview': f"Let's do a mock interview about {topic}. I'll ask you technical questions. Ready?",
        'pronunciation': f"Let's practice pronouncing terms related to {topic}. I'll give you words to pronounce.",
        'explanation': f"Explain the concept of {topic} in your own words. Take your time.",
        'debate': f"Let's debate different approaches to {topic}. What's your perspective?",
    }
    return prompts.get(scenario_type, "Let's practice!")


def _generate_ai_feedback(scenario_type, topic, transcript):
    """Generate AI feedback on user's response."""
    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        prompt = f"""You are an expert tutor evaluating a student's response.

Scenario: {scenario_type}
Topic: {topic}
Student Response: {transcript}

Provide constructive feedback on:
1. Accuracy and correctness
2. Clarity and communication
3. Depth of understanding
4. Areas for improvement

Keep feedback concise and encouraging."""

        response = llm.invoke([HumanMessage(content=prompt)])
        feedback = response.content if isinstance(response.content, str) else str(response.content)
        return feedback.strip()
    except Exception as e:
        return f"Feedback generation failed: {str(e)}"


def _calculate_score(transcript, scenario_type):
    """Calculate score for response."""
    score = 50
    
    if len(transcript) > 100:
        score += 20
    if len(transcript) > 200:
        score += 15
    if '.' in transcript:
        score += 10
    if len(transcript.split()) > 20:
        score += 5
    
    return min(100, score)


def _get_tutor_response(topic, messages):
    """Get AI tutor response."""
    try:
        model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)

        system_prompt = f"""You are a helpful AI tutor specializing in {topic}. 
Your role is to:
- Answer questions clearly and accurately
- Provide examples when helpful
- Encourage learning and curiosity
- Adapt to the student's level
- Keep responses concise but informative

Be friendly, patient, and supportive."""

        message_history = []
        for msg in messages[-5:]:
            if msg['role'] == 'user':
                message_history.append(HumanMessage(content=msg['content']))
            else:
                message_history.append(HumanMessage(content=f"Assistant: {msg['content']}"))

        response = llm.invoke(message_history)
        return response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        return f"I encountered an error: {str(e)}"

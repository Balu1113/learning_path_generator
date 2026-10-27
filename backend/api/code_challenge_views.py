import json
import requests
import time
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum
from django.utils import timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from .models import CodeChallenge, CodeSubmission
from .views import _json_body, _user_id, _path_or_none
from dotenv import load_dotenv

load_dotenv()


JUDGE0_API_URL = "https://judge0-ce.p.rapidapi.com"
JUDGE0_API_KEY = ""


def _get_judge0_headers():
    return {
        "X-RapidAPI-Key": JUDGE0_API_KEY,
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
        "Content-Type": "application/json",
    }


LANGUAGE_MAP = {
    "python": 71,
    "javascript": 63,
    "java": 62,
    "cpp": 54,
    "csharp": 51,
    "sql": 82,
    "go": 60,
    "rust": 73,
}


@require_GET
def challenges_list(request, doc_id, phase_idx):
    """List code challenges for a phase."""
    try:
        phase_idx = int(phase_idx)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid phase index"}, status=400)
    
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    
    challenges = CodeChallenge.objects.filter(
        path_id=doc_id, phase_idx=phase_idx
    ).values(
        "id", "title", "description", "difficulty", "language", "points"
    )
    
    user_submissions = {}
    if request.user.is_authenticated:
        submissions = CodeSubmission.objects.filter(
            user=request.user,
            challenge__path_id=doc_id,
            challenge__phase_idx=phase_idx
        ).values("challenge_id", "status", "score")
        user_submissions = {s["challenge_id"]: s for s in submissions}
    
    result = []
    for c in challenges:
        item = dict(c)
        if c["id"] in user_submissions:
            sub = user_submissions[c["id"]]
            item["user_status"] = sub["status"]
            item["user_score"] = sub["score"]
        result.append(item)
    
    return JsonResponse({"challenges": result})


@require_GET
def challenge_detail(request, challenge_id):
    """Get challenge details and user's current submission."""
    try:
        challenge = CodeChallenge.objects.get(id=challenge_id)
    except CodeChallenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    
    data = {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "difficulty": challenge.difficulty,
        "language": challenge.language,
        "starter_code": challenge.starter_code,
        "points": challenge.points,
        "time_limit_seconds": challenge.time_limit_seconds,
    }
    
    if request.user.is_authenticated:
        try:
            submission = CodeSubmission.objects.get(user=request.user, challenge=challenge)
            data["submission"] = {
                "id": submission.id,
                "code": submission.code,
                "status": submission.status,
                "score": submission.score,
                "passed_tests": submission.passed_tests,
                "total_tests": submission.total_tests,
                "test_results": submission.test_results,
                "error_message": submission.error_message,
            }
        except CodeSubmission.DoesNotExist:
            data["submission"] = None
    else:
        data["submission"] = None
    
    return JsonResponse(data)


@csrf_protect
@require_POST
def submission_run(request, challenge_id):
    """Run code against test cases (not submitted yet)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        challenge = CodeChallenge.objects.get(id=challenge_id)
    except CodeChallenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    
    data = _json_body(request)
    code = (data.get("code") or "").strip()
    if not code:
        return JsonResponse({"error": "Code is required"}, status=400)
    
    if len(code) > 50000:
        return JsonResponse({"error": "Code too long"}, status=400)
    
    try:
        submission, created = CodeSubmission.objects.get_or_create(
            user=request.user, challenge=challenge,
            defaults={"code": code, "status": "draft"}
        )
        if not created:
            submission.code = code
            submission.save()
    except Exception as e:
        return JsonResponse({"error": "Failed to save submission"}, status=500)
    
    test_results = []
    passed = 0
    
    for i, test in enumerate(challenge.test_cases[:20]):
        try:
            result = _run_test_case(code, test, challenge.language)
            test_results.append(result)
            if result["passed"]:
                passed += 1
        except Exception as e:
            test_results.append({
                "passed": False,
                "input": test.get("input", ""),
                "expected": test.get("output", ""),
                "actual": "",
                "error": str(e)[:200],
            })
    
    submission.test_results = test_results
    submission.passed_tests = passed
    submission.total_tests = len(test_results)
    submission.save()
    
    return JsonResponse({
        "submission_id": submission.id,
        "passed_tests": passed,
        "total_tests": len(test_results),
        "test_results": test_results,
    })


def _run_test_case(code, test, language):
    """Execute code against a single test case using Judge0."""
    if not JUDGE0_API_KEY:
        return {
            "passed": False,
            "input": test.get("input", ""),
            "expected": test.get("output", ""),
            "actual": "",
            "error": "Judge0 API not configured",
        }
    
    language_id = LANGUAGE_MAP.get(language, 71)
    stdin = test.get("input", "")
    expected_output = test.get("output", "").strip()
    
    payload = {
        "language_id": language_id,
        "source_code": code,
        "stdin": stdin,
    }
    
    try:
        response = requests.post(
            f"{JUDGE0_API_URL}/submissions",
            json=payload,
            headers=_get_judge0_headers(),
            timeout=10,
        )
        if response.status_code != 201:
            return {
                "passed": False,
                "input": stdin,
                "expected": expected_output,
                "actual": "",
                "error": "Submission failed",
            }
        
        submission_id = response.json()["id"]
        
        for _ in range(30):
            result = requests.get(
                f"{JUDGE0_API_URL}/submissions/{submission_id}",
                headers=_get_judge0_headers(),
                timeout=10,
            )
            if result.status_code == 200:
                data = result.json()
                if data.get("status", {}).get("id") not in (1, 2):
                    actual_output = (data.get("stdout") or "").strip()
                    passed = actual_output == expected_output
                    return {
                        "passed": passed,
                        "input": stdin,
                        "expected": expected_output,
                        "actual": actual_output,
                        "error": data.get("stderr", "") or data.get("compile_output", ""),
                    }
            time.sleep(0.2)
        
        return {
            "passed": False,
            "input": stdin,
            "expected": expected_output,
            "actual": "",
            "error": "Execution timeout",
        }
    except Exception as e:
        return {
            "passed": False,
            "input": stdin,
            "expected": expected_output,
            "actual": "",
            "error": str(e)[:200],
        }


@csrf_protect
@require_POST
def submission_submit(request, challenge_id):
    """Submit code challenge (final submission)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        challenge = CodeChallenge.objects.get(id=challenge_id)
    except CodeChallenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    
    try:
        submission = CodeSubmission.objects.get(user=request.user, challenge=challenge)
    except CodeSubmission.DoesNotExist:
        return JsonResponse({"error": "No submission found"}, status=404)
    
    if submission.status == "passed":
        return JsonResponse({"error": "Already passed"}, status=400)
    
    if submission.passed_tests == submission.total_tests and submission.total_tests > 0:
        submission.status = "passed"
        submission.score = challenge.points
    else:
        submission.status = "failed"
        submission.score = max(0, int((submission.passed_tests / max(1, submission.total_tests)) * challenge.points * 0.5))
    
    submission.submitted_at = timezone.now()
    submission.save()
    
    return JsonResponse({
        "status": submission.status,
        "score": submission.score,
        "passed_tests": submission.passed_tests,
        "total_tests": submission.total_tests,
    })


@require_GET
def leaderboard(request, doc_id, phase_idx):
    """Leaderboard for code challenges in a phase."""
    try:
        phase_idx = int(phase_idx)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid phase index"}, status=400)
    
    submissions = CodeSubmission.objects.filter(
        challenge__path_id=doc_id,
        challenge__phase_idx=phase_idx,
        status="passed"
    ).select_related("user").values(
        "user__username", "user__id"
    ).annotate(
        total_score=Sum("score")
    ).order_by("-total_score")[:100]
    
    return JsonResponse({
        "leaderboard": [
            {"username": s["user__username"], "score": s["total_score"]}
            for s in submissions
        ]
    })


@csrf_protect
@require_POST
def generate_code_challenges(request, doc_id, phase_idx):
    """Generate code challenges for a phase using AI."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        phase_idx = int(phase_idx)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid phase index"}, status=400)
    
    path = _path_or_none(doc_id)
    if path is None:
        return JsonResponse({"error": "Path not found"}, status=404)
    
    data = _json_body(request)
    language = (data.get("language") or "python").lower()
    difficulty = (data.get("difficulty") or "medium").lower()
    count = min(int(data.get("count") or 3), 5)
    
    if language not in ["python", "javascript", "java", "cpp", "csharp", "sql", "go", "rust"]:
        language = "python"
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"
    
    try:
        phases = path.get("phases", [])
        if not phases or phase_idx < 0 or phase_idx >= len(phases):
            phase_title = f"Phase {phase_idx + 1}"
            topic_titles = ["General"]
        else:
            phase = phases[phase_idx]
            phase_title = phase.get("title", f"Phase {phase_idx + 1}")
            topics = phase.get("topics", [])
            topic_titles = [t.get("title", "") for t in topics] or ["General"]
    except Exception as e:
        phase_title = f"Phase {phase_idx + 1}"
        topic_titles = ["General"]
    
    try:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.7)
        
        prompt = f"""Generate {count} coding challenge questions for a learning path.

Phase: {phase_title}
Topics: {', '.join(topic_titles)}
Language: {language}
Difficulty: {difficulty}

For each challenge, provide a JSON object with:
- title: Short challenge name
- description: Clear problem statement (2-3 sentences)
- difficulty: easy/medium/hard
- language: {language}
- starter_code: Starter code template
- solution_code: Working solution
- test_cases: Array of {{"input": "...", "output": "..."}} objects (3-5 test cases)
- points: Points for solving (10-20 for easy, 15-25 for medium, 20-30 for hard)

Return ONLY a valid JSON array of challenge objects, no other text.
Example format:
[
  {{
    "title": "Sum Two Numbers",
    "description": "Write a function that adds two numbers.",
    "difficulty": "easy",
    "language": "{language}",
    "starter_code": "def add(a, b):\\n    pass",
    "solution_code": "def add(a, b):\\n    return a + b",
    "test_cases": [{{"input": "2 3", "output": "5"}}],
    "points": 10
  }}
]"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        if isinstance(response.content, list):
            response_text = response.content[0].get('text', '') if response.content else ''
        else:
            response_text = response.content if isinstance(response.content, str) else str(response.content)
        
        response_text = response_text.strip()
        
        try:
            challenges_data = json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            if start >= 0 and end > start:
                try:
                    challenges_data = json.loads(response_text[start:end])
                except json.JSONDecodeError:
                    return JsonResponse({"error": f"Invalid JSON in response: {response_text[:200]}"}, status=500)
            else:
                return JsonResponse({"error": "No JSON array found in response"}, status=500)
        
        if not isinstance(challenges_data, list):
            challenges_data = [challenges_data]
        
        created_challenges = []
        for challenge_data in challenges_data[:count]:
            try:
                challenge, created = CodeChallenge.objects.get_or_create(
                    path_id=doc_id,
                    phase_idx=phase_idx,
                    title=challenge_data.get("title", "Untitled"),
                    defaults={
                        "phase_title": phase_title,
                        "description": challenge_data.get("description", ""),
                        "difficulty": challenge_data.get("difficulty", "medium"),
                        "language": challenge_data.get("language", language),
                        "starter_code": challenge_data.get("starter_code", ""),
                        "solution_code": challenge_data.get("solution_code", ""),
                        "test_cases": challenge_data.get("test_cases", []),
                        "points": challenge_data.get("points", 10),
                    }
                )
                if created:
                    created_challenges.append({
                        "id": challenge.id,
                        "title": challenge.title,
                        "difficulty": challenge.difficulty,
                        "language": challenge.language,
                        "points": challenge.points,
                    })
            except Exception as e:
                continue
        
        return JsonResponse({
            "created": len(created_challenges),
            "challenges": created_challenges,
        })
    
    except Exception as e:
        return JsonResponse({"error": f"Generation failed: {str(e)}"}, status=500)

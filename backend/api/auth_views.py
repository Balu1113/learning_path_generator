import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
import re


def _validate_username(username):
    """Validate username format and length."""
    if not username or len(username) < 3 or len(username) > 150:
        return False
    return re.match(r"^[a-zA-Z0-9_.-]+$", username) is not None


@ensure_csrf_cookie
@require_GET
def csrf_token(request):
    """Get CSRF token for POST requests."""
    from django.middleware.csrf import get_token
    return JsonResponse({"csrfToken": get_token(request)})


@csrf_protect
@require_POST
def auth_register(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request format"}, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return JsonResponse({"error": "Username and password are required"}, status=400)
    if not _validate_username(username):
        return JsonResponse({"error": "Username must be 3-150 characters, alphanumeric with . - _"}, status=400)
    if len(password) < 8:
        return JsonResponse({"error": "Password must be at least 8 characters"}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already taken"}, status=400)
    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return JsonResponse({"user": {"id": user.id, "username": user.username}})


@csrf_protect
@require_POST
def auth_login(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request format"}, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return JsonResponse({"error": "Username and password are required"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    login(request, user)
    return JsonResponse({"user": {"id": user.id, "username": user.username, "is_superuser": user.is_superuser}})


@csrf_protect
@require_POST
def auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def auth_me(request):
    if request.user.is_authenticated:
        return JsonResponse({"user": {
            "id": request.user.id,
            "username": request.user.username,
            "is_superuser": request.user.is_superuser
        }})
    return JsonResponse({"user": None})

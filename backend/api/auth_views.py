import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET


@require_POST
def auth_register(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return JsonResponse({"error": "Username and password are required"}, status=400)
    if len(password) < 6:
        return JsonResponse({"error": "Password must be at least 6 characters"}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already taken"}, status=400)
    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return JsonResponse({"user": {"id": user.id, "username": user.username}})


@require_POST
def auth_login(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid username or password"}, status=401)
    login(request, user)
    return JsonResponse({"user": {"id": user.id, "username": user.username, "is_superuser": user.is_superuser}})


@require_POST
def auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def auth_me(request):
    user = request.user
    if user.is_authenticated:
        return JsonResponse({"user": {"id": user.id, "username": user.username, "is_superuser": user.is_superuser}})
    return JsonResponse({"user": None})

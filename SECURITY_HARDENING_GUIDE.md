# Security Hardening Guide

This guide provides step-by-step instructions for implementing additional security measures beyond the core fixes already applied.

## 1. Django Security Settings

Add these to `backend/learning_path/settings.py`:

```python
# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# HTTPS & Cookies (Production only)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Security Headers
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),  # Unsafe-inline needed for React
    'style-src': ("'self'", "'unsafe-inline'"),
    'img-src': ("'self'", "data:", "https:"),
    'font-src': ("'self'",),
    'connect-src': ("'self'",),
    'frame-ancestors': ("'none'",),
}

X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY_REPORT_ONLY = False

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Allowed Hosts (Production)
if not DEBUG:
    ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
```

## 2. Rate Limiting

Install django-ratelimit:
```bash
pip install django-ratelimit
```

Add to `backend/api/auth_views.py`:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
@csrf_protect
@require_POST
def auth_login(request):
    """Login with rate limiting to prevent brute force."""
    # ... existing code ...

@ratelimit(key='ip', rate='3/m', method='POST')
@csrf_protect
@require_POST
def auth_register(request):
    """Register with rate limiting."""
    # ... existing code ...
```

Add to `backend/api/views.py`:

```python
@ratelimit(key='ip', rate='10/m', method='POST')
@csrf_protect
@require_POST
def placement_adaptive_start(request):
    """Placement test with rate limiting."""
    # ... existing code ...
```

## 3. Security Event Logging

Create `backend/api/security_logger.py`:

```python
import logging
from django.contrib.auth.models import User

# Configure security logger
security_logger = logging.getLogger('security')

def log_failed_auth(username, ip_address):
    """Log failed authentication attempt."""
    security_logger.warning(
        f"Failed login attempt",
        extra={
            'username': username,
            'ip_address': ip_address,
            'event_type': 'failed_auth',
        }
    )

def log_invalid_input(endpoint, reason, ip_address):
    """Log invalid input rejection."""
    security_logger.warning(
        f"Invalid input rejected at {endpoint}",
        extra={
            'endpoint': endpoint,
            'reason': reason,
            'ip_address': ip_address,
            'event_type': 'invalid_input',
        }
    )

def log_unauthorized_access(user_id, resource, ip_address):
    """Log unauthorized access attempt."""
    security_logger.warning(
        f"Unauthorized access attempt",
        extra={
            'user_id': user_id,
            'resource': resource,
            'ip_address': ip_address,
            'event_type': 'unauthorized_access',
        }
    )

def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

Update `backend/api/auth_views.py` to use logging:

```python
from .security_logger import log_failed_auth, get_client_ip

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
        # Log failed attempt
        log_failed_auth(username, get_client_ip(request))
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    
    login(request, user)
    return JsonResponse({
        "user": {
            "id": user.id,
            "username": user.username,
            "is_superuser": user.is_superuser
        }
    })
```

Add to `backend/learning_path/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

## 4. API Key Management

Create `.env.example`:

```
# API Keys (NEVER commit actual keys)
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-pro

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Security
SECRET_KEY=your_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

Update `config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-pro')

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")
```

## 5. CORS Configuration

Install django-cors-headers:
```bash
pip install django-cors-headers
```

Update `backend/learning_path/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
    # ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # ... rest of middleware ...
]

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Development
    "http://localhost:5173",  # Vite dev
]

if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "https://yourdomain.com",
        "https://www.yourdomain.com",
    ]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

## 6. SQL Injection Prevention

Django ORM already prevents SQL injection, but verify:

```python
# ✅ SAFE - Using ORM
User.objects.filter(username=username)

# ❌ UNSAFE - Never do this
User.objects.raw(f"SELECT * FROM auth_user WHERE username = '{username}'")

# ✅ SAFE - If raw SQL needed, use parameterized queries
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM auth_user WHERE username = %s", [username])
```

## 7. XSS Prevention (Frontend)

Ensure React components escape user input:

```jsx
// ✅ SAFE - React escapes by default
<div>{userInput}</div>

// ❌ UNSAFE - Never use dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// ✅ SAFE - If HTML needed, sanitize first
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

## 8. Dependency Security

Add to `requirements.txt`:

```
# Security scanning
safety==2.3.5
bandit==1.7.5
```

Run security checks:

```bash
# Check for known vulnerabilities
safety check

# Check for common security issues
bandit -r backend/api/

# Check dependencies
pip-audit
```

## 9. Secrets Scanning

Add `.gitignore`:

```
# Environment variables
.env
.env.local
.env.*.local

# API Keys
**/config.py
**/secrets.py

# Database
*.sqlite3
*.db

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/
```

## 10. Monitoring & Alerting

Create `backend/api/monitoring.py`:

```python
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('security')

def alert_on_suspicious_activity(event_type, details):
    """Send alert for suspicious activity."""
    if event_type == 'multiple_failed_logins':
        subject = f"⚠️ Multiple failed login attempts detected"
        message = f"""
        Suspicious Activity Alert
        
        Event: {event_type}
        Details: {details}
        
        Please review security logs immediately.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.SECURITY_ALERT_EMAIL],
            fail_silently=False,
        )
        logger.critical(f"Security alert sent: {event_type}")
```

## Deployment Checklist

- [ ] All security settings configured in settings.py
- [ ] HTTPS enabled and redirects working
- [ ] Security headers present in responses
- [ ] Rate limiting installed and configured
- [ ] Security logging configured
- [ ] API keys in environment variables
- [ ] CORS properly configured
- [ ] Dependencies scanned for vulnerabilities
- [ ] .gitignore configured
- [ ] Monitoring and alerting set up
- [ ] All 121 tests passing
- [ ] Security audit completed

## Testing Security

```bash
# Run security tests
python manage.py test api.tests

# Check for common issues
bandit -r backend/api/

# Scan dependencies
safety check

# Test CSRF protection
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
# Should return 403 Forbidden without CSRF token
```

## References

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

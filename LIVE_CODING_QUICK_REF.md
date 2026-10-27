# Live Coding Challenges - Quick Reference

## 🚀 Quick Start (5 minutes)

```bash
# 1. Set API key in .env
JUDGE0_API_KEY=your_key_here

# 2. Run migrations
python manage.py migrate

# 3. Seed sample challenges
python manage.py seed_code_challenges

# 4. Start servers
python manage.py runserver 8001  # Terminal 1
npm run dev                       # Terminal 2

# 5. Visit http://localhost:5174/study
```

## 📚 API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/paths/{id}/phases/{idx}/challenges` | GET | List challenges |
| `/api/challenges/{id}` | GET | Get challenge details |
| `/api/challenges/{id}/run` | POST | Run tests (draft) |
| `/api/challenges/{id}/submit` | POST | Submit challenge |
| `/api/paths/{id}/phases/{idx}/leaderboard` | GET | Get leaderboard |

## 💻 Supported Languages

| Language | ID | Status |
|----------|----|----|
| Python | 71 | ✅ |
| JavaScript | 63 | ✅ |
| Java | 62 | ✅ |
| C++ | 54 | ✅ |
| C# | 51 | ✅ |
| SQL | 82 | ✅ |
| Go | 60 | ✅ |
| Rust | 73 | ✅ |

## 🎯 Difficulty & Points

| Level | Points | Typical Time |
|-------|--------|--------------|
| Easy | 10 | 5-10 min |
| Medium | 15 | 15-30 min |
| Hard | 20+ | 30-60 min |

## 📊 Database Models

### CodeChallenge
```python
path_id, phase_idx, title, description
difficulty, language, starter_code, solution_code
test_cases, points, time_limit_seconds, memory_limit_mb
```

### CodeSubmission
```python
user, challenge, code, status
test_results, passed_tests, total_tests, score
execution_time_ms, error_message, submitted_at
```

## 🔧 Configuration

```python
# In .env
JUDGE0_API_KEY=your_key
JUDGE0_API_URL=https://judge0-ce.p.rapidapi.com

# In models.py
time_limit_seconds = 5
memory_limit_mb = 256
```

## 📝 Create Challenge (Django Shell)

```python
from api.models import CodeChallenge

CodeChallenge.objects.create(
    path_id="path_123",
    phase_idx=0,
    title="Sum Two Numbers",
    description="Add two numbers",
    difficulty="easy",
    language="python",
    starter_code="def add(a, b):\n    pass",
    solution_code="def add(a, b):\n    return a + b",
    test_cases=[
        {"input": "2\n3", "output": "5"},
        {"input": "10\n20", "output": "30"},
    ],
    points=10,
)
```

## 🧪 Test with cURL

```bash
# List challenges
curl http://localhost:8001/api/paths/sample_path_1/phases/0/challenges

# Run tests
curl -X POST http://localhost:8001/api/challenges/1/run \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a, b):\n    return a + b"}'

# Submit
curl -X POST http://localhost:8001/api/challenges/1/submit

# Leaderboard
curl http://localhost:8001/api/paths/sample_path_1/phases/0/leaderboard
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Judge0 API not configured" | Set `JUDGE0_API_KEY` in .env |
| "Execution timeout" | Increase `time_limit_seconds` |
| "No challenges available" | Run `seed_code_challenges` |
| Test results empty | Check browser console, verify API key |
| Challenges not appearing | Create via shell or admin panel |

## 📁 File Structure

```
backend/
├── api/
│   ├── models.py (CodeChallenge, CodeSubmission)
│   ├── code_challenge_views.py (5 endpoints)
│   ├── urls.py (5 routes)
│   ├── migrations/0010_code_challenges.py
│   └── management/commands/seed_code_challenges.py

frontend/
├── src/
│   ├── components/
│   │   ├── CodeChallengePanel.jsx
│   │   └── CodeChallenge.css
│   └── pages/Study.jsx (integrated)

docs/
├── LIVE_CODING_CHALLENGES.md
├── LIVE_CODING_SETUP.md
└── LIVE_CODING_IMPLEMENTATION.md
```

## 🎮 User Workflow

```
1. Study Workspace
   ↓
2. Select Phase
   ↓
3. View Challenges
   ↓
4. Open Challenge
   ↓
5. Write Code
   ↓
6. Run Tests (draft)
   ↓
7. Fix Errors
   ↓
8. Submit (final)
   ↓
9. View Leaderboard
```

## 🔐 Security Features

- ✅ Sandboxed execution (Judge0)
- ✅ Time limits (5 sec default)
- ✅ Memory limits (256MB default)
- ✅ Code size limits (50KB)
- ✅ Input validation
- ✅ CSRF protection
- ✅ Authentication required

## 📈 Performance

- Async execution via Judge0
- Test results cached
- Leaderboard top 100 only
- Lazy loading of details
- Efficient queries

## 🚀 Deployment

```bash
# Production checklist
- Set DEBUG=False
- Configure ALLOWED_HOSTS
- Set JUDGE0_API_KEY
- Use PostgreSQL
- Enable HTTPS
- Set up monitoring
- Configure rate limiting
```

## 📚 Documentation

| Document | Purpose | Lines |
|----------|---------|-------|
| LIVE_CODING_CHALLENGES.md | Feature docs | 400+ |
| LIVE_CODING_SETUP.md | Setup guide | 300+ |
| LIVE_CODING_IMPLEMENTATION.md | Implementation | 250+ |

## 🎯 Next Features

1. Prerequisite Visualization (Skill Graph)
2. Peer Code Review
3. Learning Streaks
4. Spaced Repetition Recommendations
5. Learning Analytics Dashboard

## 📞 Support

- Judge0 API: https://judge0.com/
- RapidAPI: https://rapidapi.com/
- Django: https://docs.djangoproject.com/
- React: https://react.dev/

## ✅ Status

**Production Ready** ✅

- All endpoints implemented
- Frontend complete
- Database migrations done
- Sample challenges seeded
- Documentation comprehensive
- Security hardened
- Performance optimized

---

**Version**: 1.0
**Status**: ✅ Production Ready
**Last Updated**: 2024

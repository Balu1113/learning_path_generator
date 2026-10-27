# Live Coding Challenges - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
# Backend - add to requirements.txt
pip install requests

# Frontend - already included
npm install
```

### 2. Configure Judge0 API

Get a free API key from RapidAPI:
1. Go to https://rapidapi.com/judge0-official/api/judge0-ce
2. Sign up for a free account
3. Subscribe to the free tier
4. Copy your API key

Add to `.env`:
```
JUDGE0_API_KEY=your_api_key_here
JUDGE0_API_URL=https://judge0-ce.p.rapidapi.com
```

### 3. Run Migrations

```bash
cd backend
python manage.py migrate
```

### 4. Seed Sample Challenges

```bash
python manage.py seed_code_challenges
```

### 5. Start the Application

```bash
# Terminal 1 - Backend
cd backend
python manage.py runserver 8001

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 6. Test the Feature

1. Open http://localhost:5174
2. Log in or create an account
3. Go to Study workspace
4. Select a path and phase
5. Scroll to "Code Challenges" section
6. Click on a challenge
7. Write code and click "Run Tests"

## Configuration Options

### Challenge Difficulty Points
Edit in `code_challenge_views.py`:
```python
DIFFICULTY_POINTS = {
    "easy": 10,
    "medium": 15,
    "hard": 20,
}
```

### Execution Limits
Edit in `models.py`:
```python
time_limit_seconds = models.IntegerField(default=5)
memory_limit_mb = models.IntegerField(default=256)
```

### Supported Languages
Add more languages in `models.py`:
```python
LANGUAGE_CHOICES = (
    ("python", "Python"),
    ("javascript", "JavaScript"),
    # Add more...
)
```

And in `code_challenge_views.py`:
```python
LANGUAGE_MAP = {
    "python": 71,
    "javascript": 63,
    # Add more...
}
```

## Creating Custom Challenges

### Via Django Shell

```bash
python manage.py shell
```

```python
from api.models import CodeChallenge

CodeChallenge.objects.create(
    path_id="your_path_id",
    phase_idx=0,
    phase_title="Phase Title",
    title="Challenge Title",
    description="Problem description here",
    difficulty="medium",
    language="python",
    starter_code="""def solution(n):
    # Your code here
    pass""",
    solution_code="""def solution(n):
    return n * 2""",
    test_cases=[
        {"input": "5", "output": "10"},
        {"input": "10", "output": "20"},
    ],
    points=15,
)
```

### Via Admin Panel

1. Go to http://localhost:8001/admin
2. Login with superuser account
3. Click "Code Challenges"
4. Click "Add Code Challenge"
5. Fill in the form
6. Save

## Troubleshooting

### Judge0 API Not Working

**Error**: "Judge0 API not configured"

**Solution**:
```bash
# Check .env file
cat .env | grep JUDGE0

# Verify API key is valid
# Test at: https://rapidapi.com/judge0-official/api/judge0-ce
```

### Code Execution Timeout

**Error**: "Execution timeout"

**Solution**:
- Increase `time_limit_seconds` in CodeChallenge model
- Check if code has infinite loops
- Verify test case input is correct

### Test Results Not Showing

**Error**: Empty test results

**Solution**:
- Check browser console for errors
- Verify Judge0 API key is set
- Check network tab for API calls
- Ensure code is valid syntax

### Challenges Not Appearing

**Error**: "No challenges available for this phase"

**Solution**:
```bash
# Seed sample challenges
python manage.py seed_code_challenges

# Or create manually via shell
python manage.py shell
# Then use the code above
```

## Performance Tuning

### Optimize Judge0 Calls

```python
# In code_challenge_views.py
# Increase timeout for slower connections
timeout=15  # was 10
```

### Cache Leaderboard

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def leaderboard(request, doc_id, phase_idx):
    # ...
```

### Batch Test Execution

```python
# Run multiple tests in parallel
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(_run_test_case, code, test, language) 
               for test in challenge.test_cases]
    test_results = [f.result() for f in futures]
```

## Monitoring

### Check API Usage

```bash
# Monitor Judge0 API calls
# Go to: https://rapidapi.com/user/account/usage

# Check rate limits
# Free tier: 50 requests/day
```

### Database Queries

```python
# In Django shell
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as context:
    # Your code here
    pass

print(f"Queries: {len(context)}")
for query in context:
    print(query['sql'])
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in settings.py
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set `JUDGE0_API_KEY` in production environment
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS
- [ ] Set up monitoring/logging
- [ ] Configure rate limiting
- [ ] Test with production data

### Docker Deployment

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV JUDGE0_API_KEY=your_key
ENV DEBUG=False

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## API Testing

### Test with cURL

```bash
# List challenges
curl http://localhost:8001/api/paths/sample_path_1/phases/0/challenges

# Get challenge details
curl http://localhost:8001/api/challenges/1

# Run tests
curl -X POST http://localhost:8001/api/challenges/1/run \
  -H "Content-Type: application/json" \
  -d '{"code": "def sum_numbers(a, b):\n    return a + b"}'

# Submit challenge
curl -X POST http://localhost:8001/api/challenges/1/submit

# Get leaderboard
curl http://localhost:8001/api/paths/sample_path_1/phases/0/leaderboard
```

### Test with Python

```python
import requests

BASE_URL = "http://localhost:8001/api"

# List challenges
response = requests.get(f"{BASE_URL}/paths/sample_path_1/phases/0/challenges")
print(response.json())

# Run tests
response = requests.post(
    f"{BASE_URL}/challenges/1/run",
    json={"code": "def sum_numbers(a, b):\n    return a + b"}
)
print(response.json())
```

## Next Steps

1. **Customize Challenges** - Create challenges for your learning paths
2. **Add More Languages** - Support additional programming languages
3. **Implement Analytics** - Track challenge completion rates
4. **Add Achievements** - Unlock badges for challenge completion
5. **Enable Collaboration** - Pair programming mode

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review LIVE_CODING_CHALLENGES.md documentation
3. Check Judge0 API documentation: https://judge0.com/
4. Review Django documentation: https://docs.djangoproject.com/

---

**Last Updated**: 2024
**Version**: 1.0

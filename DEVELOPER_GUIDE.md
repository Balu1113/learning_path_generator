# Learning Path Generator - Developer Guide

## Table of Contents
1. [Setup](#setup)
2. [Architecture](#architecture)
3. [Frontend Development](#frontend-development)
4. [Backend Development](#backend-development)
5. [Database](#database)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Contributing](#contributing)

---

## Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git
- SQLite3 (included with Python)

### Backend Setup

```bash
# Clone repository
git clone https://github.com/yourorg/learning-path-generator.git
cd learning-path-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Run migrations
cd backend
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Environment Variables

Create `.env` file:
```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-pro
DEBUG=True
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Architecture

### Project Structure

```
learning-path-generator/
├── backend/                    # Django backend
│   ├── api/                   # Main app
│   │   ├── models.py          # Database models
│   │   ├── views.py           # API endpoints
│   │   ├── urls.py            # URL routing
│   │   ├── tests.py           # Unit tests
│   │   ├── placement_adaptive.py  # Adaptive test engine
│   │   ├── skill_graph.py      # Skill tracking
│   │   ├── portfolio_views.py  # Portfolio endpoints
│   │   └── migrations/         # Database migrations
│   ├── learning_path/         # Django settings
│   ├── manage.py              # Django CLI
│   └── db.sqlite3             # Development database
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── App.jsx            # Main app
│   │   ├── index.css          # Global styles
│   │   └── mobile.css         # Mobile styles
│   ├── index.html             # HTML entry point
│   └── vite.config.js         # Vite config
├── chains/                     # LLM chains
│   └── path_generator.py      # Prompt templates
├── memory/                     # Vector store
│   └── vector_store.py        # Chroma integration
├── agents/                     # AI agents
│   └── react_agent.py         # ReAct agent
└── requirements.txt           # Python dependencies
```

### Technology Stack

**Backend**:
- Django 4.2
- Django REST Framework
- Langchain (LLM orchestration)
- Google Generative AI (Gemini)
- Chroma (vector database)
- SQLite (development)

**Frontend**:
- React 18
- Vite (build tool)
- CSS (no framework)
- Fetch API (HTTP client)

**Infrastructure**:
- Docker (optional)
- GitHub Actions (CI/CD)

---

## Frontend Development

### Component Structure

```
components/
├── Layout.jsx              # Main layout wrapper
├── PathView.jsx            # Path display
├── PlacementTest.jsx       # Placement test UI
├── PhaseTest.jsx           # Phase test UI
├── FlashcardsPanel.jsx     # Flashcard review
├── ChatPanel.jsx           # Chat interface
├── SkillsMatrix.jsx        # Skills display
├── PracticeMode.jsx        # Practice scenarios
└── ...
```

### Adding a New Page

1. Create component in `src/pages/`:
```jsx
// src/pages/MyPage.jsx
export default function MyPage() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h2>My Page</h2>
      </div>
      {/* Content */}
    </div>
  );
}
```

2. Add route in `src/App.jsx`:
```jsx
import MyPage from './pages/MyPage';

// In routes array:
{ path: '/my-page', element: <MyPage /> }
```

3. Add navigation in `src/components/Layout.jsx`:
```jsx
<a href="/my-page" className="nav-item">
  <span>📄</span>
  <span>My Page</span>
</a>
```

### Styling

- Use CSS variables from `index.css`
- Mobile-first approach in `mobile.css`
- BEM naming convention

**CSS Variables**:
```css
/* Colors */
--bg, --bg-panel, --bg-card
--text, --text-strong, --text-muted
--accent, --accent-strong, --accent-light

/* Spacing */
--radius-sm, --radius-md, --radius-lg
--shadow-sm, --shadow-md

/* Responsive */
@media (max-width: 639px) { /* Mobile */ }
@media (min-width: 640px) and (max-width: 1024px) { /* Tablet */ }
```

### API Integration

Use `src/api/client.js`:
```javascript
import * as api from './api/client.js';

// Call API
const result = await api.pathGenerate({
  goal: "Learn Python",
  current_level: "beginner",
  hours_per_day: 2,
  months: 6
});
```

### State Management

Use React hooks:
```jsx
const [paths, setPaths] = useState([]);
const [loading, setLoading] = useState(false);

useEffect(() => {
  setLoading(true);
  api.getPathHistory()
    .then(data => setPaths(data.paths))
    .finally(() => setLoading(false));
}, []);
```

---

## Backend Development

### Adding a New Endpoint

1. Create view in `api/views.py`:
```python
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

@csrf_protect
@require_POST
def my_endpoint(request):
    data = _json_body(request)
    # Process request
    return JsonResponse({"result": "success"})
```

2. Add URL in `api/urls.py`:
```python
path('my-endpoint', views.my_endpoint, name='my_endpoint'),
```

3. Add client function in `frontend/src/api/client.js`:
```javascript
export function myEndpoint(body) {
  return jsonFetch(`${API_BASE}/my-endpoint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
```

### Adding a Model

1. Create model in `api/models.py`:
```python
class MyModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
```

2. Create migration:
```bash
python manage.py makemigrations api
python manage.py migrate
```

3. Register in admin (optional):
```python
# api/admin.py
from django.contrib import admin
from .models import MyModel

admin.site.register(MyModel)
```

### LLM Integration

Use chains from `chains/path_generator.py`:

```python
from chains.path_generator import generate_learning_path

# Generate path
output = generate_learning_path(
    goal="Learn Python",
    current_level="beginner",
    hours_per_day=2,
    months=6
)
```

### Testing

```bash
# Run all tests
python manage.py test api.tests

# Run specific test
python manage.py test api.tests.AdaptivePlacementTests

# With coverage
coverage run --source='.' manage.py test api.tests
coverage report
```

### Database Queries

Use Django ORM:
```python
# Get user's paths
paths = PathProgress.objects.filter(user=request.user)

# Create record
TestResult.objects.create(
    user=request.user,
    path_id=doc_id,
    score=correct,
    total=total
)

# Update record
obj, created = MyModel.objects.update_or_create(
    user=request.user,
    defaults={'name': 'New Name'}
)
```

---

## Database

### Models Overview

**User-related**:
- `User` (Django built-in)
- `PortfolioSettings` - Privacy controls
- `Badge` - Earned badges

**Learning**:
- `PathProgress` - Topic completion tracking
- `TestResult` - Test scores
- `Flashcard` - Spaced repetition cards
- `FocusSession` - Study time tracking

**Skills**:
- `Skill` - Canonical skill definitions
- `SkillMastery` - User skill states
- `SkillEdge` - Skill prerequisites
- `PathSkill` - Topic-to-skill mapping

**Projects**:
- `MilestoneProject` - Capstone projects
- `Resource` - Curated resources

**Collaboration**:
- `StudyGroup` - Study groups
- `GroupMembership` - Group membership
- `GroupDeadline` - Shared deadlines
- `GroupCheckin` - Accountability updates

### Migrations

```bash
# Create migration
python manage.py makemigrations api --name migration_name

# Apply migrations
python manage.py migrate

# Rollback migration
python manage.py migrate api 0008

# Show migration status
python manage.py showmigrations
```

---

## Testing

### Unit Tests

```python
from django.test import TestCase
from django.contrib.auth.models import User

class MyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_something(self):
        self.assertEqual(1 + 1, 2)
```

### API Tests

```python
from django.test import Client

class APITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_endpoint(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/api/my-endpoint', {
            'data': 'value'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
```

### Running Tests

```bash
# All tests
python manage.py test

# Specific app
python manage.py test api

# Specific test class
python manage.py test api.tests.MyTests

# Specific test method
python manage.py test api.tests.MyTests.test_something

# With verbosity
python manage.py test -v 2

# With coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in settings
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Enable HTTPS
- [ ] Configure security headers
- [ ] Set up database (PostgreSQL recommended)
- [ ] Configure static files
- [ ] Set up logging
- [ ] Configure email
- [ ] Run migrations
- [ ] Collect static files
- [ ] Set up monitoring

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "learning_path.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```bash
# Build image
docker build -t learning-path-generator .

# Run container
docker run -p 8000:8000 learning-path-generator
```

### Environment Variables (Production)

```
DEBUG=False
SECRET_KEY=your_secret_key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
GEMINI_API_KEY=your_api_key
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput

# Serve with whitenoise
pip install whitenoise
```

### Database Migration (Production)

```bash
# Backup database
pg_dump dbname > backup.sql

# Run migrations
python manage.py migrate

# Restore if needed
psql dbname < backup.sql
```

---

## Contributing

### Code Style

- Python: PEP 8 (use `black` formatter)
- JavaScript: Prettier
- CSS: BEM naming convention

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "Add my feature"

# Push to remote
git push origin feature/my-feature

# Create pull request on GitHub
```

### Commit Messages

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
style: Format code
refactor: Refactor code
test: Add tests
chore: Update dependencies
```

### Pull Request Process

1. Create feature branch
2. Make changes with tests
3. Update documentation
4. Submit PR with description
5. Address review comments
6. Merge when approved

---

## Troubleshooting

### Common Issues

**Port already in use**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Database locked**:
```bash
# Remove lock file
rm db.sqlite3-journal
```

**Module not found**:
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**CORS errors**:
- Check `CORS_ALLOWED_ORIGINS` in settings
- Verify frontend URL is in allowed list

**Static files not loading**:
```bash
# Collect static files
python manage.py collectstatic
```

---

## Performance Optimization

### Database
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse relations
- Add database indexes for frequently queried fields
- Use pagination for large result sets

### Frontend
- Lazy load components
- Optimize images
- Minify CSS/JS
- Use caching headers

### Backend
- Cache API responses
- Use database connection pooling
- Optimize LLM calls
- Use async tasks for long operations

---

## Security

See [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md) for detailed security recommendations.

---

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [React Documentation](https://react.dev/)
- [Langchain Documentation](https://python.langchain.com/)
- [Google Generative AI](https://ai.google.dev/)

---

**Last Updated**: 2024
**Version**: 1.0

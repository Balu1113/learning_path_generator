# Quick Start Guide - Learning Path Generator

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### Step 1: Clone & Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start backend server
python manage.py runserver
```

Backend will be available at: `http://localhost:8000`

### Step 2: Setup Frontend

```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### Step 3: Access the Application

Open your browser and go to: `http://localhost:5173`

---

## 📋 Available Routes

### Core Features
- `/` - Agent Mode (AI-powered path generation)
- `/quick` - Quick Path (fast path creation)
- `/domains` - Domain Overview (browse learning domains)
- `/resources` - Resource Explorer (find learning resources)
- `/study` - Study (access learning materials)
- `/groups` - Study Groups (collaborate with others)
- `/portfolio` - Portfolio (view your achievements)
- `/job-target` - Job Target Mode (analyze job descriptions)

### Tier 2 Features
- `/gamification` - Gamification & Achievements (XP, levels, quests)
- `/analytics` - Learning Analytics (track progress)
- `/skills` - Skill Graph (visualize skill dependencies)
- `/peer-review` - Peer Code Review (review others' code)
- `/marketplace` - Learning Path Marketplace (buy/sell paths)
- `/videos` - Video Learning Library (watch videos)
- `/voice-tutor` - Voice Tutor & Practice (voice-based learning)
- `/practice` - Practice Scenarios (mock interviews, debugging)

### Other
- `/history` - Path History (view past paths)
- `/dashboard` - Dashboard (overview)
- `/gallery` - Gallery (browse shared paths)
- `/help` - Help (get assistance)
- `/login` - Login (authenticate)

---

## 🔑 Key Features

### 1. Adaptive Learning
- Intelligent placement tests
- Personalized learning paths
- Spaced repetition flashcards
- AI-generated study notes

### 2. Gamification
- XP and level system
- Daily quests
- Seasonal challenges
- Global leaderboards
- Learning streaks

### 3. Analytics
- Learning velocity tracking
- Weak area identification
- Cohort comparison
- Performance predictions

### 4. Collaboration
- Study groups
- Peer code review
- Shared deadlines
- Group check-ins

### 5. Advanced Features
- Job-target mode
- Practice scenarios
- Skill graph visualization
- Learning marketplace
- Voice tutor
- Video integration

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Gemini Configuration
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-3.1-flash-lite

# ChromaDB Configuration
CHROMA_PERSIST_DIR=./chroma_db

# Judge0 Configuration (optional, for code execution)
JUDGE0_API_KEY=your-judge0-key
JUDGE0_API_URL=https://judge0-ce.p.rapidapi.com

# Database (optional, for production)
DATABASE_URL=postgresql://user:password@localhost/dbname

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## 📊 API Endpoints

### Gamification
- `GET /api/gamification/level` - Get user level
- `GET /api/gamification/quests` - Get daily quests
- `GET /api/gamification/leaderboard` - Get leaderboard
- `GET /api/gamification/streak` - Get learning streak

### Analytics
- `GET /api/analytics/dashboard/<path_id>` - Get dashboard
- `GET /api/analytics/daily/<path_id>` - Get daily metrics
- `GET /api/analytics/velocity/<path_id>` - Get velocity

### Peer Review
- `GET /api/reviews/pending` - Get pending reviews
- `POST /api/reviews/create/<project_id>` - Create review
- `GET /api/reviews/reputation` - Get reputation

### Skill Graph
- `GET /api/skills/graph/<path_id>` - Get skill graph
- `GET /api/skills/blockers/<path_id>` - Get blockers
- `GET /api/skills/critical-path/<path_id>` - Get critical path

### Marketplace
- `GET /api/marketplace/browse` - Browse paths
- `GET /api/marketplace/featured` - Get featured paths
- `POST /api/marketplace/paths/<id>/purchase` - Purchase path

### Video
- `GET /api/videos/<id>` - Get video
- `POST /api/videos/<id>/progress` - Update progress
- `POST /api/videos/<id>/note` - Add note

### Voice Tutor
- `GET /api/voice/scenarios/<path_id>/<phase_idx>` - Get scenarios
- `POST /api/voice/session/start/<path_id>/<phase_idx>` - Start session
- `POST /api/voice/chat` - Start chat

### Practice Scenarios
- `GET /api/practice/scenarios/<path_id>/<phase_idx>` - Get scenarios
- `POST /api/practice/start/<path_id>/<phase_idx>` - Start scenario
- `GET /api/practice/tips` - Get tips

---

## 🧪 Testing

### Run Backend Tests
```bash
cd backend
python manage.py test api.tests
```

### Run with Coverage
```bash
coverage run --source='.' manage.py test
coverage report
```

---

## 📱 Mobile Responsive

All pages are fully responsive:
- **Mobile** (<640px): Single column layout
- **Tablet** (640-1024px): Two column layout
- **Desktop** (>1024px): Full three column layout

---

## 🌙 Dark Theme

Toggle dark/light theme using the button in the sidebar footer.

---

## 🔐 Security

- CSRF protection on all POST endpoints
- Input validation and sanitization
- Authentication required for sensitive operations
- Error message sanitization
- Secure password hashing

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
# Try a different port:
python manage.py runserver 8001
```

### Frontend won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install
npm run dev
```

### Database errors
```bash
# Reset migrations
python manage.py migrate zero api
python manage.py migrate
```

### CSRF token errors
```bash
# Clear browser cache and cookies
# Restart both servers
```

---

## 📚 Documentation

- **README.md** - Project overview
- **USER_GUIDE.md** - User documentation
- **API_DOCUMENTATION.md** - API reference
- **DEVELOPER_GUIDE.md** - Development setup
- **SECURITY_HARDENING_GUIDE.md** - Security best practices
- **COMPLETION_REPORT.md** - Complete implementation report

---

## 🎯 Next Steps

1. **Create an account** - Sign up or log in
2. **Generate a learning path** - Use Agent Mode or Quick Path
3. **Start learning** - Access study materials
4. **Track progress** - View analytics and achievements
5. **Collaborate** - Join study groups
6. **Practice** - Use practice scenarios and code challenges
7. **Share** - Create and share your portfolio

---

## 💡 Tips

- Use **Adaptive Placement Tests** to get accurate skill assessment
- Enable **Spaced Repetition** for better retention
- Join **Study Groups** for collaborative learning
- Check **Analytics** to track your progress
- Use **Practice Scenarios** to prepare for interviews
- Explore **Marketplace** for additional learning paths
- Enable **Dark Theme** for comfortable studying

---

## 🆘 Support

- Check the **Help** page for FAQs
- Review **Documentation** for detailed guides
- Check **GitHub Issues** for known problems
- Contact support@learnpath.com for assistance

---

## 🎓 Example Learning Paths

1. **Python for Data Science**
   - Python Basics → Data Structures → NumPy/Pandas → Visualization → ML Basics

2. **Full Stack Web Development**
   - HTML/CSS → JavaScript → React → Node.js → Databases → Deployment

3. **AWS Cloud Architect**
   - AWS Basics → EC2/S3 → Networking → Databases → Security → Architecture

4. **Machine Learning Engineer**
   - Math Foundations → Python → ML Algorithms → Deep Learning → NLP → Deployment

---

**Happy Learning! 🚀**

For more information, visit the documentation or contact support.

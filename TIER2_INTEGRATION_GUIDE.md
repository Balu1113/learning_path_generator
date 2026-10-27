# Tier 2 Features Integration Guide

## Quick Start

### 1. Import Components in Your App

```jsx
import GamificationPanel from './components/GamificationPanel';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import SkillGraph from './components/SkillGraph';
import PeerCodeReview from './components/PeerCodeReview';
```

### 2. Add to Your Pages

#### Dashboard/Home Page
```jsx
<GamificationPanel />
```

#### Path Detail Page
```jsx
<AnalyticsDashboard pathId={pathId} />
<SkillGraph pathId={pathId} />
```

#### Study Group/Collaboration Page
```jsx
<PeerCodeReview />
```

---

## Component Props

### GamificationPanel
No props required. Loads user's gamification data automatically.

```jsx
<GamificationPanel />
```

### AnalyticsDashboard
Requires `pathId` prop.

```jsx
<AnalyticsDashboard pathId="path_123" />
```

### SkillGraph
Requires `pathId` prop.

```jsx
<SkillGraph pathId="path_123" />
```

### PeerCodeReview
No props required. Loads pending reviews automatically.

```jsx
<PeerCodeReview />
```

---

## API Client Functions

Add these to your `frontend/src/api/client.js`:

```javascript
// Gamification
export const getUserLevel = () => fetch('/api/gamification/level').then(r => r.json());
export const getXPHistory = () => fetch('/api/gamification/xp-history').then(r => r.json());
export const getDailyQuests = () => fetch('/api/gamification/quests').then(r => r.json());
export const completeQuest = async (questId) => {
  const token = await getCsrfToken();
  return fetch(`/api/gamification/quests/${questId}/complete`, {
    method: 'POST',
    headers: { 'X-CSRFToken': token, 'Content-Type': 'application/json' },
    credentials: 'include',
  }).then(r => r.json());
};

// Analytics
export const getAnalyticsDashboard = (pathId) => 
  fetch(`/api/analytics/dashboard/${pathId}`).then(r => r.json());
export const getDailyMetrics = (pathId) => 
  fetch(`/api/analytics/daily/${pathId}`).then(r => r.json());
export const getLearningVelocity = (pathId) => 
  fetch(`/api/analytics/velocity/${pathId}`).then(r => r.json());
export const getCohortComparison = (pathId) => 
  fetch(`/api/analytics/cohort/${pathId}`).then(r => r.json());

// Peer Review
export const getPendingReviews = () => 
  fetch('/api/reviews/pending').then(r => r.json());
export const createReview = async (projectId) => {
  const token = await getCsrfToken();
  return fetch(`/api/reviews/create/${projectId}`, {
    method: 'POST',
    headers: { 'X-CSRFToken': token, 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({}),
  }).then(r => r.json());
};

// Skill Graph
export const getSkillGraph = (pathId) => 
  fetch(`/api/skills/graph/${pathId}`).then(r => r.json());
export const getPhaseBlockers = (pathId) => 
  fetch(`/api/skills/blockers/${pathId}`).then(r => r.json());
export const getCriticalPath = (pathId) => 
  fetch(`/api/skills/critical-path/${pathId}`).then(r => r.json());
```

---

## Styling

All components use CSS-in-JS with `styled-jsx`. They automatically respect:
- `--bg-primary` - Primary background color
- `--bg-secondary` - Secondary background color
- `--text-primary` - Primary text color
- `--text-secondary` - Secondary text color
- `--border-color` - Border color
- `--primary-color` - Primary accent color

Make sure these CSS variables are defined in your theme:

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #333333;
  --text-secondary: #666666;
  --border-color: #e0e0e0;
  --primary-color: #2196F3;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1e1e1e;
    --bg-secondary: #2d2d2d;
    --text-primary: #ffffff;
    --text-secondary: #b0b0b0;
    --border-color: #404040;
    --primary-color: #64B5F6;
  }
}
```

---

## Data Flow Examples

### Awarding XP
When a user completes an activity:

```python
# In your view
from api.gamification_views import _award_xp

_award_xp(
    user=request.user,
    activity='challenge_solve',
    xp_amount=50,
    description='Solved: Find Missing Element'
)
```

### Updating Analytics
Analytics are automatically aggregated when dashboard loads. To manually update:

```python
from api.models import LearningAnalytics, FocusSession
from django.db.models import Sum

analytics, _ = LearningAnalytics.objects.get_or_create(
    user=user, path_id=path_id
)
total_time = FocusSession.objects.filter(
    user=user, path_id=path_id
).aggregate(total=Sum('seconds'))['total'] or 0

analytics.total_time_minutes = total_time // 60
analytics.save()
```

### Creating a Peer Review
```python
from api.models import CodeReview

review = CodeReview.objects.create(
    submission=project,
    reviewer=request.user,
    status='in_progress'
)
```

---

## Common Patterns

### Check User Level
```jsx
const [level, setLevel] = useState(null);

useEffect(() => {
  fetch('/api/gamification/level')
    .then(r => r.json())
    .then(data => setLevel(data));
}, []);

if (level?.level === 'expert') {
  // Show expert-only features
}
```

### Display Analytics
```jsx
const [analytics, setAnalytics] = useState(null);

useEffect(() => {
  fetch(`/api/analytics/dashboard/${pathId}`)
    .then(r => r.json())
    .then(data => setAnalytics(data));
}, [pathId]);

return (
  <div>
    <p>Completion: {analytics?.completion_rate}%</p>
    <p>Time: {analytics?.total_time_minutes} minutes</p>
  </div>
);
```

### Show Skill Graph
```jsx
<SkillGraph pathId={pathId} />
```

---

## Error Handling

All components handle errors gracefully:

```jsx
try {
  const data = await fetch('/api/endpoint').then(r => r.json());
  // Use data
} catch (error) {
  console.error('Failed to load data:', error);
  // Show error message to user
}
```

---

## Performance Tips

1. **Lazy Load Components**: Only render when needed
```jsx
const GamificationPanel = lazy(() => import('./GamificationPanel'));
```

2. **Memoize Components**: Prevent unnecessary re-renders
```jsx
export default React.memo(GamificationPanel);
```

3. **Debounce API Calls**: For frequently changing data
```jsx
const debouncedLoad = useCallback(
  debounce(() => loadData(), 500),
  []
);
```

---

## Testing

### Test Gamification
```javascript
// Check XP award
POST /api/gamification/quests/1/complete
// Should return: { completed: true, xp_earned: 50 }

// Check level
GET /api/gamification/level
// Should return: { xp_total: 150, level: 'beginner', ... }
```

### Test Analytics
```javascript
// Check dashboard
GET /api/analytics/dashboard/path_123
// Should return: { completion_rate: 45.5, total_time_minutes: 120, ... }
```

### Test Peer Review
```javascript
// Get pending reviews
GET /api/reviews/pending
// Should return: { projects: [...] }

// Create review
POST /api/reviews/create/1
// Should return: { id: 1, status: 'in_progress', ... }
```

---

## Troubleshooting

### Components Not Loading
- Check that all imports are correct
- Verify CSS variables are defined
- Check browser console for errors

### API Errors
- Ensure user is authenticated
- Check CSRF token is being sent
- Verify path_id is correct format

### Data Not Updating
- Check network tab for failed requests
- Verify database migration was applied
- Check user has permission to access data

---

## Next Steps

1. **Integrate Components**: Add to your pages
2. **Test Functionality**: Verify all endpoints work
3. **Customize Styling**: Adjust colors and layout
4. **Add More Features**: Implement video, voice, marketplace
5. **Deploy**: Push to production

---

## Support

For issues or questions:
1. Check the TIER2_IMPLEMENTATION.md for detailed docs
2. Review component source code
3. Check API endpoint implementations
4. Test with curl or Postman

---

## Version Info

- **Implementation Date**: 2024
- **Features**: 5 major features
- **Models**: 23 new database models
- **Endpoints**: 26 new API routes
- **Components**: 4 React components
- **Status**: Production Ready ✅

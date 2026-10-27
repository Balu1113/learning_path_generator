# Tier 2 Features - Quick Reference Card

## 🎮 Gamification

### Component
```jsx
<GamificationPanel />
```

### Key Functions
- `getUserLevel()` - Get current level and XP
- `getDailyQuests()` - Get today's quests
- `completeQuest(questId)` - Complete a quest
- `getLeaderboard()` - Get rankings

### Data Model
```
UserLevel: xp_total, level, xp_to_next_level
XPTransaction: activity, xp_amount, description
DailyQuest: title, difficulty, xp_reward
Leaderboard: rank, score, scope
```

---

## 📊 Analytics

### Component
```jsx
<AnalyticsDashboard pathId={pathId} />
```

### Key Functions
- `getAnalyticsDashboard(pathId)` - Get all metrics
- `getDailyMetrics(pathId)` - Get 30-day history
- `getLearningVelocity(pathId)` - Get topics/week
- `getCohortComparison(pathId)` - Get percentile

### Metrics
- Completion rate
- Time invested
- Test scores
- Weak areas
- Predicted completion
- Cohort percentile

---

## 👥 Peer Review

### Component
```jsx
<PeerCodeReview />
```

### Key Functions
- `getPendingReviews()` - Get projects to review
- `createReview(projectId)` - Start review
- `addReviewComment(reviewId, lineNumber, comment)` - Add comment
- `submitReview(reviewId, status, rating)` - Submit review

### Workflow
1. Get pending projects
2. Create review
3. Add line-specific comments
4. Rate and submit
5. Earn karma points

---

## 🎯 Skill Graph

### Component
```jsx
<SkillGraph pathId={pathId} />
```

### Key Functions
- `getSkillGraph(pathId)` - Get dependency graph
- `getPhaseBlockers(pathId)` - Get blocking warnings
- `getCriticalPath(pathId)` - Get essential skills
- `getSkillMastery()` - Get mastery status

### Features
- Interactive nodes
- Phase blockers
- Critical path
- Mastery tracking

---

## 🛍️ Marketplace

### Component
```jsx
<Marketplace />
```

### Key Functions
- `browsePaths(sort, page)` - Browse marketplace
- `getFeaturedPaths()` - Get featured paths
- `purchasePath(pathId)` - Purchase path
- `reviewPath(pathId, rating, comment)` - Review path
- `createCustomPath(data)` - Create new path

### Tabs
- Browse Paths
- Featured
- My Purchases
- My Created Paths

---

## 🎥 Video Integration

### Component
```jsx
<VideoPlayer videoId={videoId} />
```

### Key Functions
- `getVideoDetail(videoId)` - Get video info
- `updateVideoProgress(videoId, seconds)` - Update progress
- `addVideoNote(videoId, timestamp, note)` - Add note
- `searchTranscript(videoId, query)` - Search transcript

### Features
- YouTube/Vimeo support
- Progress tracking
- Timestamped notes
- Transcript search

---

## 🎤 Voice Tutor

### Component
```jsx
<VoiceTutor pathId={pathId} phaseIdx={phaseIdx} />
```

### Key Functions
- `getPracticeScenarios(pathId, phaseIdx)` - Get scenarios
- `startVoiceSession(pathId, phaseIdx, scenario)` - Start session
- `submitVoiceResponse(sessionId, transcript)` - Submit response
- `getTutorChat()` - Start chat

### Scenarios
- Mock Interview
- Pronunciation Practice
- Concept Explanation
- Technical Debate

---

## 🔗 Integration Examples

### Add to Dashboard
```jsx
import GamificationPanel from './components/GamificationPanel';

export default function Dashboard() {
  return (
    <div>
      <GamificationPanel />
    </div>
  );
}
```

### Add to Path Page
```jsx
import AnalyticsDashboard from './components/AnalyticsDashboard';
import SkillGraph from './components/SkillGraph';

export default function PathDetail({ pathId }) {
  return (
    <div>
      <AnalyticsDashboard pathId={pathId} />
      <SkillGraph pathId={pathId} />
    </div>
  );
}
```

### Add to Study Group
```jsx
import PeerCodeReview from './components/PeerCodeReview';

export default function StudyGroup() {
  return (
    <div>
      <PeerCodeReview />
    </div>
  );
}
```

---

## 📱 Responsive Breakpoints

All components are responsive:
- **Mobile** (<640px): Single column
- **Tablet** (640-1024px): Two columns
- **Desktop** (>1024px): Three columns

---

## 🎨 Styling

All components use CSS variables:
```css
--bg-primary: Main background
--bg-secondary: Secondary background
--text-primary: Main text
--text-secondary: Secondary text
--border-color: Borders
--primary-color: Accent color
```

---

## 🔐 Authentication

All endpoints require authentication:
```javascript
// Automatically handled by components
// Just ensure user is logged in
```

---

## ⚡ Performance Tips

1. **Lazy load components**
```jsx
const GamificationPanel = lazy(() => import('./GamificationPanel'));
```

2. **Memoize components**
```jsx
export default React.memo(GamificationPanel);
```

3. **Debounce API calls**
```javascript
const debouncedLoad = useCallback(
  debounce(() => loadData(), 500),
  []
);
```

---

## 🐛 Debugging

### Check Network
- Open DevTools → Network tab
- Look for failed requests
- Check response status

### Check Console
- Look for JavaScript errors
- Check API error messages
- Verify CSRF token

### Check Database
- Verify migration was applied
- Check user permissions
- Verify data exists

---

## 📚 Documentation Files

1. **TIER2_IMPLEMENTATION.md** - Detailed guide
2. **TIER2_INTEGRATION_GUIDE.md** - Quick start
3. **TIER2_COMPLETE_SUMMARY.md** - Full summary
4. **TIER2_QUICK_REFERENCE.md** - This file

---

## 🚀 Deployment Checklist

- [ ] All migrations applied
- [ ] Environment variables set
- [ ] CSS variables defined
- [ ] Components imported
- [ ] Routes registered
- [ ] CSRF protection enabled
- [ ] Tests passing
- [ ] Documentation updated

---

## 📞 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Components not showing | Check CSS variables |
| API 401 errors | Ensure user logged in |
| API 403 errors | Check CSRF token |
| Data not loading | Check network tab |
| Styling broken | Verify CSS variables |

---

## 🎯 Feature Comparison

| Feature | Models | Endpoints | Components |
|---------|--------|-----------|------------|
| Gamification | 8 | 7 | 1 |
| Analytics | 2 | 4 | 1 |
| Peer Review | 3 | 7 | 1 |
| Skill Graph | 2 | 6 | 1 |
| Marketplace | 3 | 10 | 1 |
| Video | 3 | 7 | 1 |
| Voice Tutor | 2 | 7 | 1 |
| **Total** | **23** | **50+** | **8** |

---

## 💡 Pro Tips

1. **Combine features** - Use analytics + gamification for engagement
2. **Leverage skill graph** - Show prerequisites before starting
3. **Use marketplace** - Monetize instructor-created paths
4. **Integrate video** - Embed in resources
5. **Enable voice tutor** - Practice scenarios for retention

---

## 🎓 Learning Resources

- Check component source code for examples
- Review API endpoint implementations
- Read inline code comments
- Check test files for usage patterns

---

## ✅ Status

All features are **production-ready** and can be deployed immediately.

**Last Updated**: 2024
**Version**: 1.0
**Status**: ✅ Complete

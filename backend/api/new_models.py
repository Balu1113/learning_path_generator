from django.db import models
from django.conf import settings


# ============================================================================
# 2. PREREQUISITE VISUALIZATION & SKILL GRAPH
# ============================================================================

class SkillPrerequisite(models.Model):
    """Enhanced prerequisite tracking with blocking status."""
    from_skill = models.ForeignKey('Skill', on_delete=models.CASCADE, related_name='blocks')
    to_skill = models.ForeignKey('Skill', on_delete=models.CASCADE, related_name='blocked_by')
    is_critical = models.BooleanField(default=False)  # Part of critical path
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_skill', 'to_skill')


class PhaseBlocker(models.Model):
    """Tracks which phases block which phases."""
    path_id = models.CharField(max_length=100, db_index=True)
    blocking_phase_idx = models.IntegerField()
    blocked_phase_idx = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('path_id', 'blocking_phase_idx', 'blocked_phase_idx')


# ============================================================================
# 3. PEER CODE REVIEW
# ============================================================================

class CodeReview(models.Model):
    """Peer code review on project submissions."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('rejected', 'Rejected'),
    )

    submission = models.ForeignKey('MilestoneProject', on_delete=models.CASCADE, related_name='peer_reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='code_reviews_given')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    overall_rating = models.IntegerField(null=True, blank=True)  # 1-5 stars
    summary = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('submission', 'reviewer')
        indexes = [models.Index(fields=['submission', 'status'])]


class CodeReviewComment(models.Model):
    """Comment thread on specific lines of code."""
    review = models.ForeignKey(CodeReview, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    line_number = models.IntegerField()
    code_snippet = models.TextField(blank=True, default='')
    comment = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['line_number', 'created_at']
        indexes = [models.Index(fields=['review', 'line_number'])]


class UserReputation(models.Model):
    """Karma/reputation system for peer reviews."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reputation')
    
    total_karma = models.IntegerField(default=0)
    reviews_given = models.IntegerField(default=0)
    reviews_helpful = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)


# ============================================================================
# 9. LEARNING ANALYTICS DASHBOARD
# ============================================================================

class LearningAnalytics(models.Model):
    """Aggregated learning metrics per user per path."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_analytics')
    path_id = models.CharField(max_length=100, db_index=True)
    
    total_time_minutes = models.IntegerField(default=0)
    topics_completed = models.IntegerField(default=0)
    topics_total = models.IntegerField(default=0)
    
    velocity_topics_per_week = models.FloatField(default=0)
    predicted_completion_days = models.IntegerField(null=True, blank=True)
    
    weak_areas = models.JSONField(default=list, blank=True)  # List of topic keys
    cohort_percentile = models.IntegerField(null=True, blank=True)  # 0-100
    
    last_activity_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'path_id')
        indexes = [models.Index(fields=['user', 'path_id'])]


class DailyLearningMetric(models.Model):
    """Daily snapshot of learning activity."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_metrics')
    path_id = models.CharField(max_length=100, db_index=True)
    date = models.DateField()
    
    time_minutes = models.IntegerField(default=0)
    topics_completed = models.IntegerField(default=0)
    tests_taken = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'path_id', 'date')
        indexes = [models.Index(fields=['user', 'date'])]


# ============================================================================
# 10. MARKETPLACE FOR CUSTOM PATHS
# ============================================================================

class CustomPath(models.Model):
    """Instructor-created custom learning path for marketplace."""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_paths')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail_url = models.URLField(blank=True, default='')
    
    path_data = models.JSONField()  # Full path structure
    
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft')
    
    rating = models.FloatField(default=0)
    rating_count = models.IntegerField(default=0)
    purchase_count = models.IntegerField(default=0)
    
    featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', '-rating', '-purchase_count']
        indexes = [models.Index(fields=['status', 'featured'])]


class PathPurchase(models.Model):
    """Record of user purchasing a custom path."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchased_paths')
    custom_path = models.ForeignKey(CustomPath, on_delete=models.CASCADE, related_name='purchases')
    
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'custom_path')


class PathReview(models.Model):
    """User review of a custom path."""
    custom_path = models.ForeignKey(CustomPath, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    rating = models.IntegerField()  # 1-5
    comment = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('custom_path', 'user')


# ============================================================================
# 12. VIDEO INTEGRATION
# ============================================================================

class VideoResource(models.Model):
    """Video resource with progress tracking."""
    PLATFORM_CHOICES = (
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('custom', 'Custom'),
    )

    resource = models.OneToOneField('Resource', on_delete=models.CASCADE, related_name='video')
    
    platform = models.CharField(max_length=16, choices=PLATFORM_CHOICES)
    video_id = models.CharField(max_length=255)
    duration_seconds = models.IntegerField()
    
    transcript = models.TextField(blank=True, default='')
    transcript_searchable = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)


class VideoProgress(models.Model):
    """User's progress watching a video."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(VideoResource, on_delete=models.CASCADE, related_name='progress')
    
    seconds_watched = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    
    last_watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'video')


class VideoNote(models.Model):
    """Timestamped note on a video."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_notes')
    video = models.ForeignKey(VideoResource, on_delete=models.CASCADE, related_name='notes')
    
    timestamp_seconds = models.IntegerField()
    note = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp_seconds']


# ============================================================================
# 13. AI TUTOR WITH VOICE
# ============================================================================

class VoicePracticeSession(models.Model):
    """Voice-based practice scenario session."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='voice_sessions')
    path_id = models.CharField(max_length=100, db_index=True)
    phase_idx = models.IntegerField(default=0)
    
    scenario_type = models.CharField(max_length=32)  # 'mock_interview', 'pronunciation', etc.
    topic = models.CharField(max_length=255)
    
    transcript = models.TextField(blank=True, default='')
    ai_feedback = models.TextField(blank=True, default='')
    score = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'path_id'])]


class ConversationHistory(models.Model):
    """AI tutor conversation history."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    
    topic = models.CharField(max_length=255)
    messages = models.JSONField(default=list)  # [{role, content}, ...]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ============================================================================
# 15. GAMIFICATION SYSTEM
# ============================================================================

class UserLevel(models.Model):
    """User's gamification level."""
    LEVEL_CHOICES = (
        ('novice', 'Novice'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='level')
    
    xp_total = models.IntegerField(default=0)
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default='novice')
    xp_to_next_level = models.IntegerField(default=1000)
    
    updated_at = models.DateTimeField(auto_now=True)


class XPTransaction(models.Model):
    """Record of XP earned."""
    ACTIVITY_CHOICES = (
        ('topic_complete', 'Topic Completed'),
        ('test_pass', 'Test Passed'),
        ('challenge_solve', 'Challenge Solved'),
        ('review_given', 'Review Given'),
        ('quest_complete', 'Quest Completed'),
        ('streak_bonus', 'Streak Bonus'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_transactions')
    
    activity = models.CharField(max_length=32, choices=ACTIVITY_CHOICES)
    xp_amount = models.IntegerField()
    description = models.CharField(max_length=255, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'created_at'])]


class DailyQuest(models.Model):
    """Daily challenge/quest for gamification."""
    DIFFICULTY_CHOICES = (
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=16, choices=DIFFICULTY_CHOICES)
    
    xp_reward = models.IntegerField()
    requirement = models.JSONField()  # {type, count, ...}
    
    active_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-active_date']
        indexes = [models.Index(fields=['active_date'])]


class QuestProgress(models.Model):
    """User's progress on a daily quest."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quest_progress')
    quest = models.ForeignKey(DailyQuest, on_delete=models.CASCADE, related_name='progress')
    
    progress_count = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'quest')


class SeasonalChallenge(models.Model):
    """Seasonal challenge/event."""
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    xp_reward = models.IntegerField()
    leaderboard_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']


class ChallengeParticipation(models.Model):
    """User's participation in seasonal challenge."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenge_participations')
    challenge = models.ForeignKey(SeasonalChallenge, on_delete=models.CASCADE, related_name='participants')
    
    progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    rank = models.IntegerField(null=True, blank=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'challenge')


class Leaderboard(models.Model):
    """Leaderboard entry (global, cohort, or friends)."""
    SCOPE_CHOICES = (
        ('global', 'Global'),
        ('cohort', 'Cohort'),
        ('friends', 'Friends'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaderboard_entries')
    
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
    path_id = models.CharField(max_length=100, blank=True, default='')
    
    rank = models.IntegerField()
    score = models.IntegerField()
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'scope', 'path_id')
        indexes = [models.Index(fields=['scope', 'path_id', 'rank'])]


class LearningStreak(models.Model):
    """Track user's learning streak."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_streak')
    
    current_streak_days = models.IntegerField(default=0)
    longest_streak_days = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

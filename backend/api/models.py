from django.db import models
from django.conf import settings


class Feedback(models.Model):
    path_id = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    value = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("path_id", "user")


class PathProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    path_id = models.CharField(max_length=100)
    item_key = models.CharField(max_length=50)
    done = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "path_id", "item_key")


class Flashcard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="flashcards")
    path_id = models.CharField(max_length=100)
    front = models.TextField()
    back = models.TextField()
    topic = models.CharField(max_length=255, blank=True, default="")
    phase_idx = models.IntegerField(null=True, blank=True)

    ease = models.FloatField(default=2.5)
    interval_days = models.FloatField(default=0)
    reps = models.IntegerField(default=0)
    lapses = models.IntegerField(default=0)
    due_at = models.DateTimeField()
    last_review_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "path_id", "front")
        indexes = [models.Index(fields=["user", "due_at"])]


class StudyActivity(models.Model):
    KIND_CHOICES = (
        ("topic", "Topic completed"),
        ("test", "Phase test taken"),
        ("review", "Flashcard review"),
        ("path", "Path generated"),
        ("focus", "Focus session"),
        ("project", "Project milestone"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity")
    date = models.DateField()
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="topic")
    count = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "date", "kind")
        indexes = [models.Index(fields=["user", "date"])]


class TestResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    path_id = models.CharField(max_length=100)
    phase_idx = models.IntegerField(default=0)
    phase_title = models.CharField(max_length=255, blank=True, default="")
    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    percent = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class FocusSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_sessions")
    path_id = models.CharField(max_length=100)
    phase_idx = models.IntegerField(default=0)
    phase_title = models.CharField(max_length=255, blank=True, default="")
    seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"])]


class Badge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    key = models.CharField(max_length=64)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "key")


class ShareLink(models.Model):
    slug = models.CharField(max_length=32, unique=True, db_index=True)
    path_id = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="share_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "path_id")


class MilestoneProject(models.Model):
    """A scoped capstone project for one phase of a generated path, plus the
    learner's submission and AI review state."""

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("in_progress", "In progress"),
        ("submitted", "Submitted"),
        ("reviewed", "Reviewed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="milestone_projects")
    path_id = models.CharField(max_length=100, db_index=True)
    phase_idx = models.IntegerField(default=0)
    phase_title = models.CharField(max_length=255, blank=True, default="")

    title = models.CharField(max_length=255)
    brief = models.TextField()
    acceptance_criteria = models.JSONField(default=list, blank=True)
    starter_template = models.TextField(blank=True, default="")
    rubric = models.JSONField(default=list, blank=True)

    submission_url = models.CharField(max_length=500, blank=True, default="")
    submission_notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")

    ai_review = models.TextField(blank=True, default="")
    ai_score = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "path_id", "phase_idx")
        indexes = [models.Index(fields=["user", "path_id"])]


class Skill(models.Model):
    """A durable, canonical skill independent of any one generated roadmap."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True, default="")
    domain = models.CharField(max_length=80, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SkillEdge(models.Model):
    """Prerequisite edge: a learner should know `from_skill` before `to_skill`."""

    from_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="unlocks")
    to_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="required_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_skill", "to_skill")


class PathSkill(models.Model):
    """Maps one roadmap topic to one or more canonical skills."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="path_skills"
    )
    path_id = models.CharField(max_length=100, db_index=True)
    topic_key = models.CharField(max_length=50)
    topic_title = models.CharField(max_length=255, blank=True, default="")
    phase_idx = models.IntegerField(default=0)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="path_skills")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "path_id", "topic_key", "skill")
        indexes = [models.Index(fields=["user", "path_id"])]


class SkillMastery(models.Model):
    """Per-user mastery for one skill, derived from real evidence.

    States: unassessed (no row) -> developing (some evidence) -> validated
    (strong evidence: a passed phase test or a reviewed project covering the skill).
    """

    STATE_DEVELOPING = "developing"
    STATE_VALIDATED = "validated"
    STATE_CHOICES = (
        (STATE_DEVELOPING, "Developing"),
        (STATE_VALIDATED, "Validated"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skill_mastery"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="mastery")
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default=STATE_DEVELOPING)
    score = models.IntegerField(default=0)
    evidence_count = models.IntegerField(default=0)
    last_evidence_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "skill")
        indexes = [models.Index(fields=["user", "state"])]


class Resource(models.Model):
    """A curated learning resource with quality metadata.

    Entries enter the catalog as `ai_generated` candidates (from the ingest LLM)
    and are promoted to `curated` by an admin review. URL health is checked on
    ingest and re-verification; entries unverified for a long time are flagged
    stale so the UI can fall back to fresher suggestions.
    """

    SOURCE_CHOICES = (
        ("curated", "Curated"),
        ("ai_generated", "AI generated"),
    )
    HEALTH_CHOICES = (
        ("unknown", "Unknown"),
        ("ok", "OK"),
        ("redirect", "Redirected"),
        ("broken", "Broken"),
    )

    url = models.URLField(unique=True, max_length=500)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, default="article")
    level = models.CharField(max_length=16, default="beginner")
    cost = models.CharField(max_length=16, default="free")
    duration_hours = models.FloatField(null=True, blank=True)
    domain = models.CharField(max_length=80, blank=True, default="", db_index=True)
    description = models.TextField(blank=True, default="")

    content_source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default="ai_generated")
    url_health = models.CharField(max_length=16, choices=HEALTH_CHOICES, default="unknown")
    final_url = models.URLField(max_length=500, blank=True, default="")
    verified_at = models.DateTimeField(null=True, blank=True)
    community_rating = models.FloatField(null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-verified_at", "-community_rating", "name"]
        indexes = [models.Index(fields=["content_source", "url_health"])]


class StudyGroup(models.Model):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=12, unique=True, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_groups")
    path_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class GroupMembership(models.Model):
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")
        indexes = [models.Index(fields=["group", "joined_at"])]


class GroupDeadline(models.Model):
    """A shared milestone deadline for a study group."""
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="deadlines")
    title = models.CharField(max_length=200)
    due_date = models.DateField()
    description = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]
        indexes = [models.Index(fields=["group", "due_date"])]


class GroupCheckin(models.Model):
    """A brief accountability check-in from a group member."""
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="checkins")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_checkins")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["group", "created_at"])]


class PortfolioSettings(models.Model):
    """Per-user privacy controls for the public Skill Passport."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_settings"
    )
    is_public = models.BooleanField(default=False)
    show_projects = models.BooleanField(default=True)
    show_test_scores = models.BooleanField(default=True)
    show_study_hours = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "portfolio settings"


class CodeChallenge(models.Model):
    """A live coding challenge scoped to a phase, with test cases and auto-grading."""
    LANGUAGE_CHOICES = (
        ("python", "Python"),
        ("javascript", "JavaScript"),
        ("java", "Java"),
        ("cpp", "C++"),
        ("csharp", "C#"),
        ("sql", "SQL"),
        ("go", "Go"),
        ("rust", "Rust"),
    )
    DIFFICULTY_CHOICES = (
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    )

    path_id = models.CharField(max_length=100, db_index=True)
    phase_idx = models.IntegerField(default=0)
    phase_title = models.CharField(max_length=255, blank=True, default="")
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=16, choices=DIFFICULTY_CHOICES, default="medium")
    language = models.CharField(max_length=16, choices=LANGUAGE_CHOICES, default="python")
    
    starter_code = models.TextField()
    solution_code = models.TextField()
    test_cases = models.JSONField(default=list)
    time_limit_seconds = models.IntegerField(default=5)
    memory_limit_mb = models.IntegerField(default=256)
    
    points = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("path_id", "phase_idx", "title")
        indexes = [models.Index(fields=["path_id", "phase_idx"])]


class CodeSubmission(models.Model):
    """A learner's submission for a code challenge."""
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("passed", "Passed"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="code_submissions")
    challenge = models.ForeignKey(CodeChallenge, on_delete=models.CASCADE, related_name="submissions")
    
    code = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    
    test_results = models.JSONField(default=list, blank=True)
    passed_tests = models.IntegerField(default=0)
    total_tests = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    
    execution_time_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "challenge")
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["challenge", "status"])]



# ============================================================================
# 2. PREREQUISITE VISUALIZATION & SKILL GRAPH
# ============================================================================

class SkillPrerequisite(models.Model):
    """Enhanced prerequisite tracking with blocking status."""
    from_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='blocks')
    to_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='blocked_by')
    is_critical = models.BooleanField(default=False)
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

    submission = models.ForeignKey(MilestoneProject, on_delete=models.CASCADE, related_name='peer_reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='code_reviews_given')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    overall_rating = models.IntegerField(null=True, blank=True)
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
    
    weak_areas = models.JSONField(default=list, blank=True)
    cohort_percentile = models.IntegerField(null=True, blank=True)
    
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
    
    path_data = models.JSONField()
    
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
    
    rating = models.IntegerField()
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

    resource = models.OneToOneField(Resource, on_delete=models.CASCADE, related_name='video')
    
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
    
    scenario_type = models.CharField(max_length=32)
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
    messages = models.JSONField(default=list)
    
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
    requirement = models.JSONField()
    
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

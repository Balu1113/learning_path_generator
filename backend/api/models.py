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

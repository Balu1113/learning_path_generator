from django.contrib import admin
from django.utils.html import format_html

from .models import Badge, Feedback, Flashcard, FocusSession, PathProgress, StudyActivity, TestResult


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("path_id", "user", "value", "created_at")
    list_filter = ("value", "created_at")
    search_fields = ("path_id", "user__username")
    ordering = ("-created_at",)


@admin.register(PathProgress)
class PathProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "path_id", "item_key", "done", "updated_at")
    list_filter = ("done", "updated_at")
    search_fields = ("path_id", "item_key", "user__username")
    list_editable = ("done",)
    ordering = ("-updated_at",)


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("front_short", "user", "path_id", "topic", "reps", "lapses", "ease", "due_at")
    list_filter = ("due_at", "created_at")
    search_fields = ("front", "back", "path_id", "user__username")
    readonly_fields = ("created_at", "last_review_at")
    ordering = ("due_at",)

    @admin.display(description="Front")
    def front_short(self, obj):
        text = obj.front if len(obj.front) <= 60 else obj.front[:57] + "..."
        return format_html("{}", text)


@admin.register(StudyActivity)
class StudyActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "kind", "count")
    list_filter = ("kind", "date")
    search_fields = ("user__username",)
    ordering = ("-date",)


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ("user", "path_id", "phase_idx", "phase_title", "score", "total", "percent", "created_at")
    list_filter = ("percent", "created_at")
    search_fields = ("path_id", "phase_title", "user__username")
    ordering = ("-created_at",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "earned_at")
    list_filter = ("key", "earned_at")
    search_fields = ("key", "user__username")
    ordering = ("-earned_at",)


@admin.register(FocusSession)
class FocusSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "path_id", "phase_idx", "phase_title", "seconds", "created_at")
    list_filter = ("created_at",)
    search_fields = ("path_id", "phase_title", "user__username")
    ordering = ("-created_at",)


admin.site.site_header = "LearnPath Admin"
admin.site.site_title = "LearnPath Admin"
admin.site.index_title = "Manage users, feedback, paths and study data"

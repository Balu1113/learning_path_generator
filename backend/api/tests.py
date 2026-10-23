import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from .exporters import anki_csv, notion_markdown, topic_cards
from .models import Badge, Feedback, Flashcard, PathProgress, ShareLink, StudyActivity, TestResult
from .progress_stats import activity_series, record_activity, streaks
from .schedule_builder import build_schedule, path_phases, study_dates
from .sm2 import RATING_AGAIN, RATING_EASY, RATING_GOOD, sm2


def structured_path(owner=""):
    return {
        "id": "path_test",
        "content": json.dumps({
            "title": "Learn Python",
            "summary": "A test path",
            "total_weeks": 8,
            "phases": [
                {
                    "title": "Basics",
                    "description": "Core syntax",
                    "estimated_weeks": 4,
                    "topics": [
                        {"title": "Variables", "details": "types and binding",
                         "resources": [{"name": "Python docs", "type": "docs", "note": "start here"}]},
                        {"title": "Loops", "details": "for and while"},
                        {"title": "Functions", "details": "def and scope"},
                    ],
                },
                {
                    "title": "Advanced",
                    "description": "Go deeper",
                    "estimated_weeks": 4,
                    "topics": [
                        {"title": "Decorators", "details": "wrapping functions"},
                        {"title": "Generators", "details": "lazy sequences"},
                    ],
                },
            ],
        }),
        "metadata": {
            "goal": "Learn Python",
            "format": "structured",
            "hours_per_day": 2,
            "months": 3,
            "created_at": str(date.today().isoformat()),
            **({"owner": owner} if owner else {}),
        },
    }


class Sm2Tests(TestCase):
    def test_good_review_builds_interval(self):
        ease, interval, reps, lapses, due = sm2(2.5, 0, 0, 0, RATING_GOOD)
        self.assertEqual(reps, 1)
        self.assertEqual(interval, 1)
        self.assertEqual(ease, 2.5)

        ease, interval, reps, _, _ = sm2(ease, interval, reps, 0, RATING_GOOD)
        self.assertEqual(reps, 2)
        self.assertEqual(interval, 6)

        ease, interval, reps, _, _ = sm2(ease, interval, reps, 0, RATING_GOOD)
        self.assertEqual(reps, 3)
        self.assertEqual(interval, 15)

    def test_again_resets_and_lapses(self):
        ease, interval, reps, lapses, due = sm2(2.5, 15, 4, 0, RATING_AGAIN)
        self.assertEqual(reps, 0)
        self.assertEqual(lapses, 1)
        self.assertEqual(interval, 0)
        self.assertLess(due.isoformat()[:10], (date.today() + timedelta(days=1)).isoformat())

    def test_easy_raises_ease(self):
        ease, *_ = sm2(2.5, 6, 2, 0, RATING_EASY)
        self.assertGreater(ease, 2.5)

    def test_ease_never_drops_below_floor(self):
        ease = 2.5
        interval, reps = 6, 2
        for _ in range(30):
            ease, interval, reps, _, _ = sm2(ease, interval, reps, 0, RATING_AGAIN)
        self.assertGreaterEqual(ease, 1.3)


class ScheduleTests(TestCase):
    def test_study_dates_keeps_weekdays_only(self):
        days = study_dates(date(2026, 1, 5), 5, 14)
        self.assertEqual(len(days), 14)
        self.assertEqual(len(set(days)), 14)
        self.assertEqual(days[0], date(2026, 1, 5))
        self.assertEqual(days[5], date(2026, 1, 12))
        for d in days:
            self.assertLess(d.weekday(), 5)

    def test_study_dates_start_on_rest_day_skips_to_next(self):
        days = study_dates(date(2026, 1, 10), 5, 3)
        self.assertEqual(days[0], date(2026, 1, 12))

    def test_schedule_blocks_have_real_dates(self):
        schedule = build_schedule(structured_path(), start=date(2026, 1, 5), days_per_week=5)
        self.assertGreaterEqual(schedule["total_blocks"], 5)
        self.assertEqual(len(schedule["days"]), schedule["total_blocks"])
        for day in schedule["days"]:
            date.fromisoformat(day["date"])
            self.assertTrue(day["blocks"])
            self.assertGreater(day["hours"], 0)

    def test_phase_windows_respect_estimated_weeks(self):
        schedule = build_schedule(structured_path(), start=date(2026, 1, 5), days_per_week=5)
        self.assertEqual(schedule["phases"], ["Basics", "Advanced"])
        dates = [date.fromisoformat(d["date"]) for d in schedule["days"]]
        self.assertGreaterEqual(min(dates), date(2026, 1, 5))
        self.assertGreaterEqual(max(dates), date(2026, 2, 10))
        self.assertLessEqual(max(dates), date(2026, 3, 1))

    def test_path_phases_for_markdown(self):
        path = structured_path()
        path["metadata"]["format"] = "markdown"
        path["content"] = "# Learning Plan\n\n## Phase 1: Basics\n\n- Variables\n- Loops\n\n## Phase 2: Advanced\n\n- Decorators\n"
        phases = path_phases(path)
        self.assertEqual([p["title"] for p in phases], ["Basics", "Advanced"])
        self.assertEqual(len(phases[0]["topics"]), 2)


class ExportTests(TestCase):
    def test_anki_csv_has_header_and_rows(self):
        cards = topic_cards(structured_path())
        self.assertEqual(len(cards), 5)
        body = anki_csv(cards, deck_name="Learn Python")
        lines = [l for l in body.strip().split("\n") if not l.startswith("#")]
        self.assertEqual(len(lines), 5)
        self.assertIn("Variables", lines[0])
        self.assertIn("Python docs", lines[0])

    def test_notion_markdown_uses_checkboxes(self):
        body = notion_markdown(structured_path())
        self.assertIn("- [ ]", body)
        self.assertIn("## Phase 1: Basics", body)
        self.assertIn("### Variables", body)


class StreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="streaky", password="x")

    def test_current_and_longest_streak(self):
        today = date.today()
        for offset in (2, 1, 0):
            StudyActivity.objects.create(user=self.user, date=today - timedelta(days=offset), kind="topic")
        info = streaks(self.user)
        self.assertEqual(info["current"], 3)
        self.assertEqual(info["longest"], 3)

        StudyActivity.objects.create(user=self.user, date=today - timedelta(days=10), kind="topic")
        info = streaks(self.user)
        self.assertEqual(info["current"], 3)
        self.assertEqual(info["longest"], 3)

    def test_series_counts_days(self):
        record_activity(self.user, "topic")
        series = activity_series(self.user, days=7)
        self.assertEqual(len(series), 7)
        self.assertEqual(series[-1]["count"], 1)
        self.assertEqual(series[-1]["kinds"], {"topic": 1})

    def test_record_activity_increments_same_day(self):
        record_activity(self.user, "topic")
        record_activity(self.user, "topic")
        record_activity(self.user, "test")
        row = StudyActivity.objects.get(user=self.user, kind="topic")
        self.assertEqual(row.count, 2)
        series = activity_series(self.user, days=1)
        self.assertEqual(series[-1]["count"], 3)
        self.assertEqual(series[-1]["kinds"], {"topic": 2, "test": 1})

    def test_anonymous_streak_is_zero(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(streaks(AnonymousUser())["current"], 0)


class BadgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="earner", password="x")

    def test_perfect_test_badge_is_earned_once(self):
        from .badges import evaluate
        TestResult.objects.create(user=self.user, path_id="p", percent=100, score=5, total=5)
        badges = {b["key"]: b for b in evaluate(self.user)}
        self.assertTrue(badges["perfect-test"]["earned"])
        self.assertFalse(badges["streak-7"]["earned"])
        self.assertEqual(Badge.objects.filter(user=self.user, key="perfect-test").count(), 1)

        evaluate(self.user)
        self.assertEqual(Badge.objects.filter(user=self.user, key="perfect-test").count(), 1)

    def test_phase_one_complete_badge(self):
        from unittest.mock import patch

        from .badges import evaluate

        path = structured_path(owner=str(self.user.id))
        with patch("api.badges.vector_memory") as memory:
            memory.get_recent_paths.return_value = []
            memory.get_path.return_value = {
                "id": "path_test",
                "content": path["content"],
                "metadata": path["metadata"],
            }
            self.assertNotIn("phase-1-complete", {b["key"] for b in evaluate(self.user) if b["earned"]})
            for i in range(3):
                PathProgress.objects.create(user=self.user, path_id="path_test", item_key=f"t:0:{i}")
            earned = {b["key"] for b in evaluate(self.user) if b["earned"]}
            self.assertIn("phase-1-complete", earned)


class FlashcardModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carder", password="x")

    def test_due_flag_and_unique_front(self):
        from datetime import datetime, timezone

        from django.db import transaction

        now = datetime.now(tz=timezone.utc)
        Flashcard.objects.create(user=self.user, path_id="p", front="Q", back="A", due_at=now)
        with self.assertRaises(Exception):
            with transaction.atomic():
                Flashcard.objects.create(user=self.user, path_id="p", front="Q", back="B", due_at=now)

        due = Flashcard.objects.filter(user=self.user, due_at__lte=now)
        self.assertEqual(due.count(), 1)


class ApiEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="x")
        self.path = structured_path(owner=str(self.user.id))

    def _login(self):
        self.client.force_login(self.user)

    def test_streak_requires_login(self):
        self.assertEqual(self.client.get("/api/streak").status_code, 401)
        self._login()
        resp = self.client.get("/api/streak?days=30")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["series"]), 30)
        self.assertIn("current_streak", data)

    def test_badges_endpoint(self):
        self._login()
        resp = self.client.get("/api/badges")
        self.assertEqual(resp.status_code, 200)
        keys = [b["key"] for b in resp.json()["badges"]]
        self.assertIn("phase-1-complete", keys)
        self.assertIn("streak-7", keys)

    def test_flashcard_due_and_review_cycle(self):
        from datetime import datetime, timezone as dt_timezone

        now = datetime.now(tz=dt_timezone.utc)
        card = Flashcard.objects.create(
            user=self.user, path_id="p", front="What is a closure?", back="A function plus its scope",
            due_at=now,
        )
        self._login()

        due = self.client.get("/api/flashcards/due").json()
        self.assertEqual(due["count"], 1)
        self.assertEqual(due["cards"][0]["id"], card.id)

        resp = self.client.post(f"/api/flashcards/{card.id}/review", data=json.dumps({"rating": 2}),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["card"]["reps"], 1)
        self.assertEqual(body["card"]["interval_days"], 1)
        self.assertEqual(body["remaining_due"], 0)
        self.assertTrue(
            StudyActivity.objects.filter(user=self.user, kind="review").exists()
        )

    def test_flashcard_review_rejects_other_users(self):
        from datetime import datetime, timezone as dt_timezone

        other = User.objects.create_user(username="other", password="x")
        card = Flashcard.objects.create(
            user=other, path_id="p", front="Q", back="A",
            due_at=datetime.now(tz=dt_timezone.utc),
        )
        self._login()
        resp = self.client.post(f"/api/flashcards/{card.id}/review", data=json.dumps({"rating": 1}),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_schedule_and_ics_export(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/schedule?start=2026-01-05&days_per_week=5")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertGreater(data["total_blocks"], 0)
            self.assertEqual(data["days"][0]["date"], "2026-01-05")

            ics = self.client.get("/api/paths/path_test/schedule.ics?start=2026-01-05")
            self.assertEqual(ics.status_code, 200)
            self.assertIn("text/calendar", ics["Content-Type"])
            self.assertIn("DTSTART;VALUE=DATE:20260105", ics.content.decode())
            self.assertIn("BEGIN:VEVENT", ics.content.decode())
            self.assertIn("Study: ", ics.content.decode())

    def test_export_endpoints(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            anki = self.client.get("/api/paths/path_test/export/anki")
            self.assertEqual(anki.status_code, 200)
            self.assertIn("text/csv", anki["Content-Type"])
            self.assertIn("Variables", anki.content.decode())

            notion = self.client.get("/api/paths/path_test/export/notion")
            self.assertEqual(notion.status_code, 200)
            self.assertIn("- [ ]", notion.content.decode())
            self.assertIn(".md", notion["Content-Disposition"])

    def test_history_includes_version_fields(self):
        from unittest.mock import patch

        self._login()
        with patch("api.views.vector_memory") as memory:
            memory.get_recent_paths.return_value = [{
                "id": "path_1",
                "content": self.path["content"],
                "metadata": dict(self.path["metadata"], lineage="path_1", version="3"),
            }]
            data = self.client.get("/api/paths/history").json()
        self.assertEqual(data["paths"][0]["lineage"], "path_1")
        self.assertEqual(data["paths"][0]["version"], 3)

    def test_regenerate_creates_next_version(self):
        from unittest.mock import patch

        self._login()
        parent = {
            "id": "path_1",
            "content": self.path["content"],
            "metadata": dict(self.path["metadata"], format="structured", version="1"),
        }
        with patch("api.study_views._path_or_none", return_value=parent), \
                patch("api.study_views.generate_learning_path_structured",
                      return_value={"title": "New", "phases": []}) as gen, \
                patch("api.study_views.vector_memory") as memory, \
                patch("api.views.vector_memory", memory):
            memory.save_path.return_value = "path_2"
            resp = self.client.post("/api/paths/path_1/regenerate", data="{}", content_type="application/json")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body["version"], 2)
            self.assertEqual(body["lineage"], "path_1")
            self.assertEqual(memory.save_path.call_count, 1)
            saved_meta = memory.save_path.call_args.kwargs["meta"]
            self.assertEqual(saved_meta["lineage"], "path_1")
            self.assertEqual(saved_meta["version"], "2")
            gen.assert_called_once()

    def test_phase_test_submit_records_result_and_activity(self):
        self._login()
        session = self.client.session
        session["test_quiz1"] = {
            "path_id": "path_1",
            "phase_idx": 0,
            "phase_title": "Basics",
            "questions": [
                {"id": "q1", "answer_index": 0},
                {"id": "q2", "answer_index": 1},
            ],
        }
        session.save()

        resp = self.client.post("/api/tests/submit", data=json.dumps({
            "quiz_id": "quiz1",
            "answers": {"q1": 0, "q2": 1},
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["percent"], 100)
        self.assertTrue(TestResult.objects.filter(user=self.user, percent=100).exists())
        self.assertTrue(StudyActivity.objects.filter(user=self.user, kind="test").exists())
        earned = {b["key"] for b in resp.json()["badges"] if b["earned"]}
        self.assertIn("perfect-test", earned)


class WorkspaceApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="wsuser", password="x")
        self.path = structured_path(owner=str(self.user.id))

    def _login(self):
        self.client.force_login(self.user)

    def test_workspace_structured_phases_and_keys(self):
        from unittest.mock import patch

        self._login()
        with patch("api.views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/workspace")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["goal"], "Learn Python")
        self.assertEqual(data["format"], "structured")
        self.assertEqual(len(data["phases"]), 2)
        phase0 = data["phases"][0]
        self.assertEqual(phase0["title"], "Basics")
        self.assertEqual(phase0["topics"][0]["key"], "t:0:0")
        self.assertEqual(phase0["topics"][0]["resources"][0]["name"], "Python docs")
        self.assertEqual(data["done"], [])

    def test_workspace_includes_saved_progress(self):
        from unittest.mock import patch

        PathProgress.objects.create(
            user=self.user, path_id="path_test", item_key="t:0:1", done=True,
        )
        self._login()
        with patch("api.views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/workspace")
        self.assertEqual(resp.json()["done"], ["t:0:1"])

    def test_workspace_markdown_topics_and_links(self):
        from unittest.mock import patch

        md_path = {
            "id": "path_md",
            "content": (
                "# Roadmap\n\n"
                "## Phase 1: Foundations\n\n"
                "- Variables and types\n"
                "- [MDN JS guide](https://developer.mozilla.org/en-US/docs/Web/JavaScript)\n"
                "- Functions and scope\n\n"
                "## Phase 2: Next\n\n"
                "- Async patterns\n"
            ),
            "metadata": {"goal": "Learn JS", "format": "markdown"},
        }
        with patch("api.views._path_or_none", return_value=md_path):
            resp = self.client.get("/api/paths/path_md/workspace")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["phases"]), 2)
        p0 = data["phases"][0]
        self.assertEqual(p0["title"], "Foundations")
        self.assertEqual([t["title"] for t in p0["topics"]], [
            "Variables and types", "MDN JS guide", "Functions and scope",
        ])
        self.assertEqual(p0["topics"][1]["resources"][0]["note"],
                         "https://developer.mozilla.org/en-US/docs/Web/JavaScript")
        self.assertEqual(p0["topics"][0]["key"], "t:0:0")

    def test_workspace_markdown_phase_without_bullets_gets_placeholder(self):
        from unittest.mock import patch

        md_path = {
            "id": "path_md2",
            "content": "# Roadmap\n\n## Phase 1: Reading\n\nJust some prose about studying.\n\n## Phase 2: More\n\n- One topic\n",
            "metadata": {"goal": "Read", "format": "markdown"},
        }
        with patch("api.views._path_or_none", return_value=md_path):
            resp = self.client.get("/api/paths/path_md2/workspace")
        self.assertEqual(resp.status_code, 200)
        p0 = resp.json()["phases"][0]
        self.assertEqual(len(p0["topics"]), 1)
        self.assertEqual(p0["topics"][0]["key"], "t:0:0")

    def test_workspace_requires_access(self):
        from unittest.mock import patch

        with patch("api.views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/workspace")
        self.assertEqual(resp.status_code, 403)

    def test_workspace_404_when_missing(self):
        from unittest.mock import patch

        with patch("api.views._path_or_none", return_value=None):
            resp = self.client.get("/api/paths/missing/workspace")
        self.assertEqual(resp.status_code, 404)


class StudyNotesTests(TestCase):
    def setUp(self):
        import time as _time

        self.user = User.objects.create_user(username="notesuser", password="x")
        self.path = structured_path(owner=str(self.user.id))
        self.path["id"] = f"path_notes_{int(_time.time() * 1000)}"
        self.url = f"/api/paths/{self.path['id']}/study-notes"

    def _login(self):
        self.client.force_login(self.user)

    def _post(self, body):
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_notes_generate_then_serve_from_cache(self):
        from unittest.mock import patch

        self._login()
        md = "## Variables — Core Notes\n\n### The big idea\n\nDeep content here."
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.study_views.generate_study_notes", return_value=md) as gen:
            resp = self._post({"phase_idx": 0, "topic_idx": 0, "depth": 1})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["section"], md)
        self.assertEqual(data["depth"], 1)
        self.assertTrue(data["has_more"])
        self.assertFalse(data["cached"])
        gen.assert_called_once()

        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.study_views.generate_study_notes") as gen2:
            resp2 = self._post({"phase_idx": 0, "topic_idx": 0, "depth": 1})
        gen2.assert_not_called()
        self.assertEqual(resp2.json()["section"], md)
        self.assertTrue(resp2.json()["cached"])

    def test_notes_deeper_level_appends_and_passes_covered(self):
        from unittest.mock import patch

        self._login()
        level1 = "## Variables — Core Notes\n\nCore body."
        level2 = "## Variables — Deep Dive 2\n\nAdvanced body."
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.study_views.generate_study_notes", side_effect=[level1, level2]) as gen:
            first = self._post({"phase_idx": 0, "topic_idx": 0}).json()
            second = self._post({"phase_idx": 0, "topic_idx": 0, "depth": 2}).json()
        self.assertEqual(first["depth"], 1)
        self.assertEqual(second["section"], level2)
        covered_arg = gen.call_args.kwargs.get("covered") or gen.call_args[1].get("covered")
        self.assertIn("Variables — Core Notes", covered_arg)

    def test_notes_last_level_has_no_more(self):
        from unittest.mock import patch

        self._login()
        md = "## X — Deep Dive 4\n\nBody."
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.study_views.generate_study_notes", return_value=md):
            data = self._post({"phase_idx": 0, "topic_idx": 0, "depth": 4}).json()
        self.assertFalse(data["has_more"])
        self.assertEqual(data["depth"], 4)

    def test_notes_invalid_indices(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            self.assertEqual(self._post({"phase_idx": 9, "topic_idx": 0}).status_code, 404)
            self.assertEqual(self._post({"phase_idx": 0, "topic_idx": 9}).status_code, 404)
            self.assertEqual(self._post({"phase_idx": "x", "topic_idx": 0}).status_code, 400)

    def test_notes_requires_path_access(self):
        from unittest.mock import patch

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self._post({"phase_idx": 0, "topic_idx": 0})
        self.assertEqual(resp.status_code, 403)


class AdminApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="secret123")
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save()
        self.regular = User.objects.create_user(username="regular1", password="secret123")

    @staticmethod
    def _post(client, url, payload):
        return client.post(url, data=json.dumps(payload), content_type="application/json")

    def test_anonymous_and_regular_users_are_forbidden(self):
        from django.test import Client

        anon = Client()
        self.assertEqual(anon.get("/api/admin/users/").status_code, 403)

        member = Client()
        member.force_login(self.regular)
        self.assertEqual(member.get("/api/admin/users/").status_code, 403)
        self.assertEqual(member.get("/api/admin/counts/").status_code, 403)
        self.assertEqual(member.get("/api/admin/_meta/").status_code, 403)

    def test_meta_and_counts(self):
        self.client.force_login(self.admin)
        meta = self.client.get("/api/admin/_meta/").json()
        self.assertIn("users", meta["resources"])
        self.assertIn("paths", meta["resources"])
        field_names = {f["name"] for f in meta["resources"]["feedback"]["fields"]}
        self.assertEqual(field_names, {"path_id", "user", "value"})
        user_field = next(f for f in meta["resources"]["users"]["fields"] if f["name"] == "password")
        self.assertTrue(user_field["write_only"])

        counts = self.client.get("/api/admin/counts/").json()
        self.assertEqual(counts["users"], 2)
        self.assertEqual(counts["superusers"], 1)
        self.assertIn("paths", counts)

    def test_user_create_update_delete(self):
        self.client.force_login(self.admin)
        resp = self._post(self.client, "/api/admin/users/", {"username": "newbie", "password": "secret123"})
        self.assertEqual(resp.status_code, 201)
        uid = resp.json()["result"]["id"]
        created = User.objects.get(pk=uid)
        self.assertTrue(created.check_password("secret123"))

        resp = self.client.put(f"/api/admin/users/{uid}/",
                               data=json.dumps({"is_active": False, "email": "n@example.com"}),
                               content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        created.refresh_from_db()
        self.assertFalse(created.is_active)
        self.assertEqual(created.email, "n@example.com")

        resp = self.client.delete(f"/api/admin/users/{uid}/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(pk=uid).exists())

    def test_user_create_requires_valid_password(self):
        self.client.force_login(self.admin)
        resp = self._post(self.client, "/api/admin/users/", {"username": "nopass"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.json()["errors"])

        resp = self._post(self.client, "/api/admin/users/", {"username": "shorty", "password": "abc"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.json()["errors"])

    def test_cannot_delete_own_account(self):
        self.client.force_login(self.admin)
        resp = self.client.delete(f"/api/admin/users/{self.admin.pk}/")
        self.assertEqual(resp.status_code, 400)

    def test_feedback_crud_and_validation(self):
        self.client.force_login(self.admin)
        resp = self._post(self.client, "/api/admin/feedback/",
                          {"path_id": "path_1", "user": self.regular.pk, "value": 5})
        self.assertEqual(resp.status_code, 201)
        fid = resp.json()["result"]["id"]
        row = Feedback.objects.get(pk=fid)
        self.assertEqual(row.user_id, self.regular.pk)
        self.assertEqual(row.value, 5)
        self.assertEqual(resp.json()["result"]["user_label"], "regular1")

        dup = self._post(self.client, "/api/admin/feedback/",
                         {"path_id": "path_1", "user": self.regular.pk, "value": 1})
        self.assertEqual(dup.status_code, 400)
        dup_errors = dup.json()["errors"]
        self.assertTrue(any("already exists" in str(msgs) for msgs in dup_errors.values()))

        unknown = self._post(self.client, "/api/admin/feedback/",
                             {"path_id": "path_2", "user": self.regular.pk, "value": 3, "bogus": 1})
        self.assertEqual(unknown.status_code, 400)
        self.assertIn("bogus", unknown.json()["errors"])

        bad_fk = self._post(self.client, "/api/admin/feedback/",
                            {"path_id": "path_2", "user": 999999, "value": 3})
        self.assertEqual(bad_fk.status_code, 400)
        self.assertIn("user", bad_fk.json()["errors"])

        listing = self.client.get("/api/admin/feedback/").json()
        self.assertEqual(listing["count"], 1)

        resp = self.client.delete(f"/api/admin/feedback/{fid}/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Feedback.objects.filter(pk=fid).exists())

    def test_list_search_sort_and_pagination(self):
        self.client.force_login(self.admin)
        for i in range(3):
            Feedback.objects.create(path_id=f"path_{i}", user=self.regular, value=i)
            StudyActivity.objects.create(
                user=self.regular, date=date.today() - timedelta(days=i), kind="topic", count=i + 1
            )

        resp = self.client.get("/api/admin/feedback/?search=path_1")
        self.assertEqual(resp.json()["count"], 1)

        resp = self.client.get("/api/admin/feedback/?page_size=2&page=1")
        body = resp.json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["results"]), 2)

        resp = self.client.get("/api/admin/feedback/?page_size=2&page=2")
        self.assertEqual(len(resp.json()["results"]), 1)

        resp = self.client.get("/api/admin/feedback/?sort=bogus")
        self.assertEqual(resp.status_code, 400)

        resp = self.client.get("/api/admin/activity/")
        self.assertEqual(resp.json()["count"], 3)

        resp = self.client.get("/api/admin/nope/")
        self.assertEqual(resp.status_code, 404)

    def test_paths_crud(self):
        from unittest.mock import patch

        self.client.force_login(self.admin)
        store = {
            "path_1": {"id": "path_1", "content": "old content",
                       "metadata": {"goal": "Learn Python", "created_at": "100.0", "format": "markdown"}},
        }

        def fake_save(goal, content, meta=None):
            store["path_2"] = {"id": "path_2", "content": content,
                               "metadata": {"goal": goal, "created_at": "200.0", **(meta or {})}}
            return "path_2"

        with patch("api.admin_api.vector_memory") as memory:
            memory.get_recent_paths.return_value = list(store.values())
            memory.get_path.side_effect = lambda doc_id: store.get(doc_id)
            memory.save_path.side_effect = fake_save
            memory.count_paths.return_value = len(store)
            memory.update_path.return_value = True
            memory.delete_path.return_value = True

            listing = self.client.get("/api/admin/paths/").json()
            self.assertEqual(listing["count"], 1)
            self.assertNotIn("content", listing["results"][0])

            created = self._post(self.client, "/api/admin/paths/",
                                 {"goal": "Learn Rust", "content": "# Rust"})
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json()["result"]["id"], "path_2")

            missing = self._post(self.client, "/api/admin/paths/", {"goal": "", "content": ""})
            self.assertEqual(missing.status_code, 400)
            self.assertIn("goal", missing.json()["errors"])

            detail = self.client.get("/api/admin/paths/path_1/").json()
            self.assertEqual(detail["result"]["content"], "old content")

            updated = self.client.put("/api/admin/paths/path_1/",
                                      data=json.dumps({"goal": "Learn Python", "content": "new content"}),
                                      content_type="application/json")
            self.assertEqual(updated.status_code, 200)
            memory.update_path.assert_called_once()
            self.assertEqual(memory.update_path.call_args.args[0], "path_1")
            self.assertEqual(memory.update_path.call_args.args[1], "new content")

            not_found = self.client.get("/api/admin/paths/path_9/")
            self.assertEqual(not_found.status_code, 404)

            deleted = self.client.delete("/api/admin/paths/path_1/")
            self.assertEqual(deleted.status_code, 200)
            memory.delete_path.assert_called_once_with("path_1")



class AdaptiveApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="adaptive", password="x")
        self.other = User.objects.create_user(username="bystander", password="x")
        self.path = structured_path(owner=str(self.user.id))

    def _login(self, user=None):
        self.client.force_login(user or self.user)

    @staticmethod
    def _post(url, payload):
        return json.dumps(payload)

    def test_focus_log_requires_login_and_valid_seconds(self):
        resp = self.client.post("/api/focus/log", data=self._post("/api/focus/log", {
            "path_id": "path_1", "seconds": 600,
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 401)

        self._login()
        resp = self.client.post("/api/focus/log", data=self._post("/api/focus/log", {
            "path_id": "path_1", "seconds": 5,
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_focus_log_records_session_and_activity(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.post("/api/focus/log", data=self._post("/api/focus/log", {
                "path_id": "path_test", "phase_idx": 1, "phase_title": "Advanced",
                "seconds": 1500,
            }), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["logged_seconds"], 1500)
        self.assertEqual(body["today_seconds"], 1500)
        from .models import FocusSession
        self.assertTrue(FocusSession.objects.filter(
            user=self.user, path_id="path_test", phase_idx=1, seconds=1500,
        ).exists())
        self.assertTrue(StudyActivity.objects.filter(user=self.user, kind="focus").exists())

    def test_focus_summary_aggregates_by_phase(self):
        from unittest.mock import patch
        from .models import FocusSession

        self._login()
        FocusSession.objects.create(user=self.user, path_id="p", phase_idx=0, seconds=600)
        FocusSession.objects.create(user=self.user, path_id="p", phase_idx=1, seconds=900)
        FocusSession.objects.create(user=self.other, path_id="p", phase_idx=0, seconds=9999)

        resp = self.client.get("/api/focus/summary?path_id=p")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total_seconds"], 1500)
        self.assertEqual(body["today_seconds"], 1500)
        phases = {e["phase_idx"]: e["seconds"] for e in body["by_phase"]}
        self.assertEqual(phases, {0: 600, 1: 900})

    def test_deadline_alerts_flag_behind_pace(self):
        import time as _time
        from datetime import timedelta
        from unittest.mock import patch

        self._login()
        created = _time.time() - timedelta(days=40).total_seconds()
        target = (date.today() + timedelta(days=10)).isoformat()
        behind = dict(self.path, id="path_behind")
        behind["metadata"] = dict(
            self.path["metadata"], format="structured",
            created_at=str(created), target_date=target,
        )
        no_target = dict(self.path, id="path_notarget")
        no_target["metadata"] = dict(self.path["metadata"], format="structured", created_at=str(created))
        foreign = dict(self.path, id="path_foreign")
        foreign["metadata"] = dict(
            self.path["metadata"], format="structured", owner=str(self.other.id),
            created_at=str(created), target_date=target,
        )
        with patch("api.adaptive_views.vector_memory") as memory:
            memory.get_recent_paths.return_value = [behind, no_target, foreign]
            resp = self.client.get("/api/deadlines/alerts")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["checked"], 1)
        self.assertEqual(len(body["alerts"]), 1)
        alert = body["alerts"][0]
        self.assertEqual(alert["path_id"], "path_behind")
        self.assertEqual(alert["actual_pct"], 0)
        self.assertGreaterEqual(alert["expected_pct"], 70)
        self.assertIn(alert["status"], ("behind", "critical", "overdue"))

    def test_deadline_alerts_calm_when_ahead_of_pace(self):
        import time as _time
        from unittest.mock import patch

        self._login()
        p = dict(self.path, id="path_calm")
        p["metadata"] = dict(
            self.path["metadata"], format="structured",
            created_at=str(_time.time()), target_date=(date.today() + timedelta(days=90)).isoformat(),
        )
        with patch("api.adaptive_views.vector_memory") as memory:
            memory.get_recent_paths.return_value = [p]
            resp = self.client.get("/api/deadlines/alerts")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["alerts"], [])

    def test_remediation_quiz_generated_from_missed_questions(self):
        from unittest.mock import patch

        self._login()
        with patch("api.views._path_or_none", return_value=self.path), \
                patch("api.views._can_access", return_value=True), \
                patch("api.views.generate_phase_quiz") as gen:
            gen.return_value = {"questions": [
                {"id": "q1", "question": "What is a variable?", "options": ["a", "b", "c", "d"], "answer_index": 0},
                {"id": "q2", "question": "What is a loop?", "options": ["a", "b", "c", "d"], "answer_index": 1},
            ]}
            resp = self.client.post("/api/paths/path_1/phases/0/test",
                                    data="{}", content_type="application/json")
            quiz = resp.json()
            resp = self.client.post("/api/tests/submit", data=json.dumps({
                "quiz_id": quiz["quiz_id"],
                "answers": {quiz["questions"][0]["id"]: 0, quiz["questions"][1]["id"]: 0},
            }), content_type="application/json")
        body = resp.json()
        self.assertIsNotNone(body.get("remediation"))
        self.assertEqual(body["remediation"]["count"], 1)
        self.assertEqual(body["remediation"]["questions"][0]["id"], quiz["questions"][1]["id"])
        remed_id = body["remediation"]["quiz_id"]

        resp = self.client.post("/api/tests/submit", data=json.dumps({
            "quiz_id": remed_id,
            "answers": {body["remediation"]["questions"][0]["id"]: 1},
        }), content_type="application/json")
        self.assertEqual(resp.json()["percent"], 100)
        self.assertIsNone(resp.json().get("remediation"))

    def test_no_remediation_when_perfect_score(self):
        from unittest.mock import patch

        self._login()
        with patch("api.views._path_or_none", return_value=self.path), \
                patch("api.views._can_access", return_value=True), \
                patch("api.views.generate_phase_quiz") as gen:
            gen.return_value = {"questions": [
                {"id": "q1", "question": "Q?", "options": ["a", "b"], "answer_index": 0},
            ]}
            resp = self.client.post("/api/paths/path_1/phases/0/test",
                                    data="{}", content_type="application/json")
            quiz = resp.json()
            resp = self.client.post("/api/tests/submit", data=json.dumps({
                "quiz_id": quiz["quiz_id"], "answers": {"q1": 0},
            }), content_type="application/json")
        self.assertIsNone(resp.json().get("remediation"))
        self.assertEqual(resp.json()["percent"], 100)

    def test_difficulty_analysis_verdicts(self):
        from unittest.mock import patch

        self._login()
        TestResult.objects.create(user=self.user, path_id="path_test", phase_idx=0, score=2, total=5, percent=40)
        TestResult.objects.create(user=self.user, path_id="path_test", phase_idx=1, score=5, total=5, percent=100)
        TestResult.objects.create(user=self.user, path_id="path_test", phase_idx=1, score=5, total=5, percent=95)
        TestResult.objects.create(user=self.other, path_id="path_test", phase_idx=1, score=0, total=5, percent=0)

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/difficulty")
        self.assertEqual(resp.status_code, 200)
        phases = resp.json()["phases"]
        self.assertEqual(phases[0]["verdict"], "too_hard")
        self.assertEqual(phases[0]["attempts"], 1)
        self.assertEqual(phases[1]["verdict"], "too_easy")
        self.assertEqual(phases[1]["attempts"], 2)

    def test_difficulty_requires_login(self):
        resp = self.client.get("/api/paths/path_test/difficulty")
        self.assertEqual(resp.status_code, 401)

    def test_retune_rewrites_phase_and_saves_new_version(self):
        from unittest.mock import patch

        self._login()
        new_phase = {
            "title": "Basics (simplified)",
            "description": "Easier step-by-step",
            "estimated_weeks": 4,
            "topics": [{"title": "Variables", "details": "gentler intro", "resources": []}],
        }
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.adaptive_views._retune_phase_llm", return_value=new_phase) as llm, \
                patch("api.adaptive_views.vector_memory") as memory, \
                patch("api.views.vector_memory", memory):
            memory.save_path.return_value = "path_retuned"
            resp = self.client.post("/api/paths/path_test/retune", data=json.dumps({
                "phase_idx": 0, "direction": "easier",
            }), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["id"], "path_retuned")
        self.assertEqual(body["version"], 2)
        self.assertEqual(body["phase_idx"], 0)
        self.assertEqual(body["direction"], "easier")
        llm.assert_called_once()
        saved_doc = memory.save_path.call_args.args[1]
        self.assertIn("Basics (simplified)", saved_doc)
        self.assertEqual(memory.save_path.call_args.kwargs["meta"]["retuned_phase"], "0")

    def test_retune_rejects_markdown_and_bad_phase(self):
        from unittest.mock import patch

        self._login()
        md = dict(self.path, id="path_md")
        md["metadata"] = dict(self.path["metadata"], format="markdown")
        with patch("api.study_views._path_or_none", return_value=md):
            resp = self.client.post("/api/paths/path_md/retune", data=json.dumps({
                "phase_idx": 0, "direction": "easier",
            }), content_type="application/json")
            self.assertEqual(resp.status_code, 400)

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.post("/api/paths/path_test/retune", data=json.dumps({
                "phase_idx": 99, "direction": "easier",
            }), content_type="application/json")
            self.assertEqual(resp.status_code, 404)

    def test_retune_infers_direction_from_scores(self):
        from unittest.mock import patch

        self._login()
        TestResult.objects.create(user=self.user, path_id="path_test", phase_idx=0, score=2, total=5, percent=40)
        new_phase = {"title": "Basics", "description": "d", "estimated_weeks": 4, "topics": []}
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.adaptive_views._retune_phase_llm", return_value=new_phase) as llm, \
                patch("api.adaptive_views.vector_memory") as memory, \
                patch("api.views.vector_memory", memory):
            memory.save_path.return_value = "path_x"
            resp = self.client.post("/api/paths/path_test/retune", data=json.dumps({
                "phase_idx": 0,
            }), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["direction"], "easier")
        self.assertEqual(llm.call_args.args[2], "easier")


class ShareLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sharer", password="x")
        self.other = User.objects.create_user(username="viewer", password="x")
        self.path = structured_path(owner=str(self.user.id))

    def _login(self, user=None):
        self.client.force_login(user or self.user)

    def test_share_endpoints_require_login(self):
        resp = self.client.get("/api/paths/path_test/share")
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/paths/path_test/share", data="{}",
                                content_type="application/json")
        self.assertEqual(resp.status_code, 401)
        resp = self.client.delete("/api/paths/path_test/share")
        self.assertEqual(resp.status_code, 401)

    def test_owner_creates_and_reuses_link(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.post("/api/paths/path_test/share", data="{}",
                                    content_type="application/json")
        body = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(body["created"])
        slug = body["slug"]
        self.assertTrue(body["url"].endswith(slug))
        self.assertTrue(ShareLink.objects.filter(slug=slug, path_id="path_test",
                                                  user=self.user).exists())

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/share")
        self.assertEqual(resp.json()["slug"], slug)
        self.assertTrue(resp.json()["created"])

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.post("/api/paths/path_test/share", data="{}",
                                    content_type="application/json")
        self.assertEqual(resp.json()["slug"], slug)
        self.assertFalse(resp.json()["created"])

    def test_non_owner_cannot_share(self):
        from unittest.mock import patch

        self._login(self.other)
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.post("/api/paths/path_test/share", data="{}",
                                    content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_share_unknown_path_is_404(self):
        self._login()
        resp = self.client.post("/api/paths/path_does_not_exist/share", data="{}",
                                content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_public_fetch_returns_readonly_payload(self):
        from unittest.mock import patch

        ShareLink.objects.create(user=self.user, path_id="path_test", slug="abc123XYZ")
        with patch("api.share_views.vector_memory") as memory:
            memory.get_path.return_value = self.path
            resp = self.client.get("/api/share/abc123XYZ")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["id"], "path_test")
        self.assertEqual(body["goal"], "Learn Python")
        self.assertEqual(body["format"], "structured")
        self.assertIn("phases", body["content"])
        self.assertNotIn("owner", body["metadata"])
        memory.get_path.assert_called_once_with("path_test")

    def test_revoked_and_unknown_slugs_are_404(self):
        from unittest.mock import patch

        ShareLink.objects.create(user=self.user, path_id="path_test", slug="revoked1")
        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.delete("/api/paths/path_test/share")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["revoked"])
        self.assertFalse(ShareLink.objects.filter(slug="revoked1").exists())

        resp = self.client.get("/api/share/revoked1")
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get("/api/share/never-existed")
        self.assertEqual(resp.status_code, 404)

    def test_deleting_path_removes_share_links(self):
        from unittest.mock import patch

        ShareLink.objects.create(user=self.user, path_id="path_test", slug="doomed1")
        self._login()
        with patch("api.views._path_or_none", return_value=self.path):
            resp = self.client.delete("/api/paths/path_test/delete")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ShareLink.objects.filter(slug="doomed1").exists())


class GalleryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="curator", password="x")
        self.path = structured_path(owner=str(self.user.id))
        self.md_path = {
            "id": "path_md",
            "content": "# Roadmap\n\n## Phase 1: Start\n- learn a\n- learn b\n\n"
                       "## Phase 2: Go\n- learn c\n",
            "metadata": {
                "goal": "MD goal",
                "format": "markdown",
                "created_at": str(date.today().isoformat()),
            },
        }

    def test_gallery_is_public_and_counts_phases_and_topics(self):
        from unittest.mock import patch

        ShareLink.objects.create(user=self.user, path_id="path_test", slug="slugA")
        ShareLink.objects.create(user=self.user, path_id="path_md", slug="slugB")
        paths = {"path_test": self.path, "path_md": self.md_path}
        with patch("api.share_views.vector_memory") as memory:
            memory.get_path.side_effect = lambda pid: paths.get(pid)
            resp = self.client.get("/api/gallery")
        self.assertEqual(resp.status_code, 200)
        items = {i["slug"]: i for i in resp.json()["items"]}
        self.assertEqual(set(items), {"slugA", "slugB"})

        a = items["slugA"]
        self.assertEqual(a["goal"], "Learn Python")
        self.assertEqual(a["title"], "Learn Python")
        self.assertEqual(a["format"], "structured")
        self.assertEqual(a["phase_count"], 2)
        self.assertEqual(a["topic_count"], 5)
        self.assertNotIn("owner", a)
        self.assertNotIn("content", a)

        md = items["slugB"]
        self.assertEqual(md["goal"], "MD goal")
        self.assertEqual(md["phase_count"], 2)
        self.assertEqual(md["topic_count"], 3)
        self.assertNotIn("owner", md)

    def test_gallery_skips_deleted_paths(self):
        from unittest.mock import patch

        ShareLink.objects.create(user=self.user, path_id="gone", slug="goneSlug")
        ShareLink.objects.create(user=self.user, path_id="path_test", slug="okSlug")
        with patch("api.share_views.vector_memory") as memory:
            memory.get_path.side_effect = lambda pid: self.path if pid == "path_test" else None
            resp = self.client.get("/api/gallery")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([i["slug"] for i in resp.json()["items"]], ["okSlug"])

    def test_gallery_newest_share_first(self):
        from unittest.mock import patch
        from django.utils import timezone

        old = ShareLink.objects.create(user=self.user, path_id="path_old", slug="oldSlug")
        ShareLink.objects.create(user=self.user, path_id="path_new", slug="newSlug")
        ShareLink.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=1),
        )
        with patch("api.share_views.vector_memory") as memory:
            memory.get_path.return_value = self.path
            resp = self.client.get("/api/gallery")
        self.assertEqual(
            [i["slug"] for i in resp.json()["items"]],
            ["newSlug", "oldSlug"],
        )

    def test_gallery_empty_when_nothing_shared(self):
        resp = self.client.get("/api/gallery")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["items"], [])


class StudyGroupTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="leader", password="x")
        self.member = User.objects.create_user(username="teammate", password="x")
        self.outsider = User.objects.create_user(username="stranger", password="x")
        self.path = structured_path(owner=str(self.owner.id))

    def _login(self, user):
        self.client.force_login(user)

    @staticmethod
    def _post(url, payload=None):
        return json.dumps(payload or {})

    def _req(self, url, payload=None, method="POST"):
        return self.client.generic(
            method, url, self._post(url, payload), content_type="application/json",
        )

    def _create_group(self, user=None, name="Study Buddies"):
        self._login(user or self.owner)
        resp = self._req("/api/groups/create", {"name": name})
        self.assertEqual(resp.status_code, 200)
        return resp.json()["group"]

    def test_create_requires_login(self):
        resp = self._req("/api/groups/create", {"name": "x"})
        self.assertEqual(resp.status_code, 401)

    def test_create_group_with_owner_membership(self):
        g = self._create_group()
        self.assertEqual(g["member_count"], 1)
        self.assertTrue(g["is_owner"])
        self.assertEqual(len(g["code"]), 6)
        self.assertEqual(g["owner_name"], "leader")
        self.assertEqual(g["name"], "Study Buddies")

    def test_create_requires_name(self):
        self._login(self.owner)
        resp = self._req("/api/groups/create", {"name": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_join_by_code_case_insensitive_and_bad_code(self):
        g = self._create_group()
        self._login(self.member)
        resp = self._req("/api/groups/join", {"code": g["code"].lower()})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["joined"])
        resp = self._req("/api/groups/join", {"code": g["code"]})
        self.assertFalse(resp.json()["joined"])
        resp = self._req("/api/groups/join", {"code": "NOPE99"})
        self.assertEqual(resp.status_code, 404)

    def test_list_only_shows_my_groups(self):
        g = self._create_group()
        self._login(self.member)
        self._req("/api/groups/join", {"code": g["code"]})
        resp = self.client.get("/api/groups")
        self.assertEqual([x["id"] for x in resp.json()["groups"]], [g["id"]])
        self._login(self.outsider)
        resp = self.client.get("/api/groups")
        self.assertEqual(resp.json()["groups"], [])

    def test_detail_requires_membership(self):
        g = self._create_group()
        self._login(self.outsider)
        resp = self.client.get(f"/api/groups/{g['id']}")
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get("/api/groups/999999")
        self.assertEqual(resp.status_code, 404)

    def test_detail_shows_member_progress_on_group_path(self):
        from unittest.mock import patch
        from .models import PathProgress

        g = self._create_group()
        self._login(self.member)
        self._req("/api/groups/join", {"code": g["code"]})

        self._login(self.owner)
        with patch("api.group_views.vector_memory") as memory, \
                patch("api.study_views._path_or_none", return_value=self.path):
            memory.get_path.return_value = self.path
            resp = self._req(f"/api/groups/{g['id']}/path", {"path_id": "path_test"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["path_goal"], "Learn Python")
        for key in ("t:0:0", "t:0:1"):
            PathProgress.objects.create(user=self.owner, path_id="path_test",
                                        item_key=key, done=True)

        self._login(self.member)
        with patch("api.group_views.vector_memory") as memory:
            memory.get_path.return_value = self.path
            body = self.client.get(f"/api/groups/{g['id']}").json()
        self.assertEqual(body["path_goal"], "Learn Python")
        by_name = {m["username"]: m for m in body["members"]}
        self.assertTrue(by_name["leader"]["is_owner"])
        self.assertEqual(by_name["leader"]["progress"]["percent"], 40)
        self.assertEqual(by_name["leader"]["progress"]["total"], 5)
        self.assertEqual(by_name["teammate"]["progress"]["percent"], 0)

    def test_only_owner_sets_path_and_path_must_be_accessible(self):
        from unittest.mock import patch

        g = self._create_group()
        self._login(self.member)
        self._req("/api/groups/join", {"code": g["code"]})
        resp = self._req(f"/api/groups/{g['id']}/path", {"path_id": "path_test"})
        self.assertEqual(resp.status_code, 403)

        self._login(self.owner)
        other_path = structured_path(owner=str(self.outsider.id))
        with patch("api.study_views._path_or_none", return_value=other_path):
            resp = self._req(f"/api/groups/{g['id']}/path", {"path_id": "path_test"})
        self.assertEqual(resp.status_code, 403)

        resp = self._req(f"/api/groups/{g['id']}/path", {"path_id": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["path_id"], "")

    def test_leave_transfers_ownership_then_deletes_empty_group(self):
        from .models import StudyGroup as GroupModel

        g = self._create_group()
        self._login(self.member)
        self._req("/api/groups/join", {"code": g["code"]})

        self._login(self.owner)
        resp = self._req(f"/api/groups/{g['id']}/leave")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"left": True, "group_deleted": False})
        self.assertEqual(GroupModel.objects.get(id=g["id"]).owner_id, self.member.id)

        self._login(self.member)
        resp = self._req(f"/api/groups/{g['id']}/leave")
        self.assertEqual(resp.json(), {"left": True, "group_deleted": True})
        self.assertFalse(GroupModel.objects.filter(id=g["id"]).exists())

    def test_leave_requires_membership(self):
        g = self._create_group()
        self._login(self.outsider)
        resp = self._req(f"/api/groups/{g['id']}/leave")
        self.assertEqual(resp.status_code, 403)

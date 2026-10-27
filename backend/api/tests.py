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

    def test_recommendation_uses_progress_then_requires_phase_evidence(self):
        """The next-step API is ordered, explainable, and never infers mastery from a checkbox."""
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/recommendation")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["state"], "learn")
            self.assertEqual(resp.json()["topic_title"], "Variables")

            for item_key in ("t:0:0", "t:0:1", "t:0:2"):
                PathProgress.objects.create(
                    user=self.user, path_id="path_test", item_key=item_key, done=True,
                )
            resp = self.client.get("/api/paths/path_test/recommendation")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["state"], "validate")

            TestResult.objects.create(
                user=self.user, path_id="path_test", phase_idx=0, percent=40,
            )
            resp = self.client.get("/api/paths/path_test/recommendation")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["state"], "remediate")
            self.assertEqual(resp.json()["score"], 40)

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


class ProjectApiTests(TestCase):
    """Project-based milestones: generation, submission, AI review, and the build state."""

    def setUp(self):
        self.user = User.objects.create_user(username="builder", password="x")
        self.other = User.objects.create_user(username="stranger", password="x")
        self.path = structured_path(owner=str(self.user.id))

    def _login(self, user=None):
        self.client.force_login(user or self.user)

    def _req(self, url, payload=None, method="POST"):
        data = json.dumps(payload or {})
        if method == "GET":
            return self.client.get(url)
        return self.client.post(url, data=data, content_type="application/json")

    @staticmethod
    def _spec(title="Todo CLI"):
        return {
            "title": title,
            "brief": "Build a small CLI that manages a todo list.",
            "acceptance_criteria": ["Add a task", "List tasks", "Mark done"],
            "starter_template": "todo/\n  main.py\n  README.md",
            "rubric": [
                {"criterion": "Functionality", "max_points": 60, "description": "works end to end"},
                {"criterion": "Code quality", "max_points": 40, "description": "clean and tested"},
            ],
        }

    def test_generate_creates_project_for_phase(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.project_views.generate_phase_project", return_value=self._spec()):
            resp = self._req("/api/paths/path_test/projects/generate", {"phase_idx": 0})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["created"], 1)
        self.assertEqual(body["projects"][0]["title"], "Todo CLI")
        self.assertEqual(body["projects"][0]["status"], "draft")
        row = MilestoneProject.objects.get(user=self.user, path_id="path_test", phase_idx=0)
        self.assertEqual(row.phase_title, "Basics")
        self.assertEqual(len(row.acceptance_criteria), 3)

    def test_generate_all_skips_existing_and_respects_force(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        self._login()
        MilestoneProject.objects.create(
            user=self.user, path_id="path_test", phase_idx=0,
            phase_title="Basics", title="Old", brief="old brief",
        )
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.project_views.generate_phase_project", return_value=self._spec("New")):
            resp = self._req("/api/paths/path_test/projects/generate", {})
        body = resp.json()
        self.assertEqual(body["existing"], 1)
        self.assertEqual(body["created"], 1)
        self.assertEqual(body["projects"][0]["title"], "Old")

        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.project_views.generate_phase_project", return_value=self._spec("New")):
            resp = self._req("/api/paths/path_test/projects/generate", {"phase_idx": 0, "force": True})
        body = resp.json()
        self.assertEqual(body["updated"], 1)
        row = MilestoneProject.objects.get(user=self.user, path_id="path_test", phase_idx=0)
        self.assertEqual(row.title, "New")
        self.assertEqual(row.status, "draft")

    def test_generate_rejects_invalid_llm_output(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.project_views.generate_phase_project", return_value={"nope": 1}):
            resp = self._req("/api/paths/path_test/projects/generate", {"phase_idx": 0})
        self.assertEqual(resp.status_code, 502)

    def test_generate_requires_login_and_valid_phase(self):
        from unittest.mock import patch

        resp = self._req("/api/paths/path_test/projects/generate", {"phase_idx": 0})
        self.assertEqual(resp.status_code, 401)

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            self.assertEqual(
                self._req("/api/paths/path_test/projects/generate", {"phase_idx": 9}).status_code, 404,
            )

    def test_list_and_detail(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        MilestoneProject.objects.create(
            user=self.user, path_id="path_test", phase_idx=1,
            phase_title="Advanced", title="Decorators lib", brief="Build a decorator library.",
            status="in_progress",
        )
        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            body = self._req("/api/paths/path_test/projects", method="GET").json()
            self.assertEqual(body["total"], 1)
            self.assertEqual(body["projects"][0]["phase_idx"], 1)

            detail = self._req("/api/paths/path_test/projects/1", method="GET").json()
            self.assertEqual(detail["project"]["title"], "Decorators lib")

            missing = self._req("/api/paths/path_test/projects/0", method="GET")
            self.assertEqual(missing.status_code, 404)

    def test_other_users_project_is_not_visible(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        MilestoneProject.objects.create(
            user=self.other, path_id="path_test", phase_idx=0,
            phase_title="Basics", title="Secret", brief="not yours",
        )
        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            body = self._req("/api/paths/path_test/projects", method="GET").json()
            self.assertEqual(body["total"], 0)
            resp = self._req("/api/paths/path_test/projects/0", method="GET")
            self.assertEqual(resp.status_code, 404)
            submit = self._req("/api/paths/path_test/projects/0/submit", {"submission_notes": "x"})
            self.assertEqual(submit.status_code, 404)

    def test_submit_validates_and_sets_status(self):
        from unittest.mock import patch
        from .models import MilestoneProject, StudyActivity

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self._req("/api/paths/path_test/projects/0/submit", {})
            self.assertEqual(resp.status_code, 404)

            MilestoneProject.objects.create(
                user=self.user, path_id="path_test", phase_idx=0,
                phase_title="Basics", title="Todo CLI", brief="brief",
            )
            resp = self._req("/api/paths/path_test/projects/0/submit", {})
            self.assertEqual(resp.status_code, 400)

            resp = self._req("/api/paths/path_test/projects/0/submit", {"submission_url": "ftp://bad"})
            self.assertEqual(resp.status_code, 400)

            resp = self._req("/api/paths/path_test/projects/0/submit", {
                "submission_url": "https://github.com/me/todo",
                "submission_notes": "Added, list, done commands.",
            })
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["project"]["status"], "submitted")
            row = MilestoneProject.objects.get(user=self.user, path_id="path_test", phase_idx=0)
            self.assertEqual(row.submission_url, "https://github.com/me/todo")
            self.assertTrue(StudyActivity.objects.filter(user=self.user, kind="project").exists())

    def test_review_scores_clamps_and_earns_badge(self):
        from unittest.mock import patch
        from .models import Badge, MilestoneProject

        self._login()
        row = MilestoneProject.objects.create(
            user=self.user, path_id="path_test", phase_idx=0,
            phase_title="Basics", title="Todo CLI", brief="brief",
            status="submitted", submission_notes="I built it.",
        )
        result = {
            "score": 150,
            "review": "Solid work. Next: add tests.",
            "criteria_met": ["Add a task"],
            "criteria_missed": [{"criterion": "List tasks", "why": "no evidence"}],
        }
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.project_views.review_phase_project", return_value=result):
            resp = self._req("/api/paths/path_test/projects/0/review")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["score"], 100)
        self.assertEqual(body["project"]["status"], "reviewed")
        row.refresh_from_db()
        self.assertEqual(row.ai_score, 100)
        self.assertTrue(row.reviewed_at)
        self.assertTrue(Badge.objects.filter(user=self.user, key="project-shipped").exists())
        self.assertEqual(body["criteria_missed"][0]["criterion"], "List tasks")

    def test_review_requires_submitted_status(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        self._login()
        MilestoneProject.objects.create(
            user=self.user, path_id="path_test", phase_idx=0,
            phase_title="Basics", title="Todo CLI", brief="brief", status="draft",
        )
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self._req("/api/paths/path_test/projects/0/review")
        self.assertEqual(resp.status_code, 400)

    def test_resubmission_clears_previous_review(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        self._login()
        MilestoneProject.objects.create(
            user=self.user, path_id="path_test", phase_idx=0,
            phase_title="Basics", title="Todo CLI", brief="brief",
            status="reviewed", ai_review="old", ai_score=40,
        )
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self._req("/api/paths/path_test/projects/0/submit", {"submission_notes": "v2"})
        self.assertEqual(resp.status_code, 200)
        row = MilestoneProject.objects.get(pk=resp.json()["project"]["id"])
        self.assertEqual(row.status, "submitted")
        self.assertEqual(row.ai_review, "")
        self.assertIsNone(row.ai_score)

    def test_recommendation_returns_build_state_for_unreviewed_project(self):
        from unittest.mock import patch
        from .models import MilestoneProject

        self._login()
        for key in ("t:0:0", "t:0:1", "t:0:2"):
            PathProgress.objects.create(user=self.user, path_id="path_test", item_key=key, done=True)
        TestResult.objects.create(
            user=self.user, path_id="path_test", phase_idx=0, percent=85, score=5, total=5,
        )
        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self._req("/api/paths/path_test/recommendation", method="GET")
            body = resp.json()
            self.assertEqual(body["state"], "learn")
            self.assertEqual(body["phase_idx"], 1)

            MilestoneProject.objects.create(
                user=self.user, path_id="path_test", phase_idx=0,
                phase_title="Basics", title="Todo CLI", brief="brief", status="draft",
            )
            resp = self._req("/api/paths/path_test/recommendation", method="GET")
            body = resp.json()
            self.assertEqual(body["state"], "build")
            self.assertEqual(body["topic_title"], "Todo CLI")
            self.assertEqual(body["project_status"], "draft")

            MilestoneProject.objects.filter(
                user=self.user, path_id="path_test", phase_idx=0,
            ).update(status="reviewed")
            resp = self._req("/api/paths/path_test/recommendation", method="GET")
            body = resp.json()
            self.assertEqual(body["state"], "learn")
            self.assertEqual(body["phase_idx"], 1)


class SkillGraphTests(TestCase):
    """Skill graph extraction, prerequisite edges, and mastery states."""

    def setUp(self):
        self.user = User.objects.create_user(username="skillful", password="x")
        self.path = structured_path(owner=str(self.user.id))

    def _login(self):
        self.client.force_login(self.user)

    def _graph(self):
        return {
            "skills": [
                {"name": "Python", "slug": "python", "description": "Core Python",
                 "domain": "programming", "prerequisites": []},
                {"name": "Unit Testing", "slug": "unit-testing", "description": "Testing in Python",
                 "domain": "programming", "prerequisites": ["python"]},
            ],
            "topic_map": [
                {"topic_key": "t:0:0", "skill_slugs": ["python"]},
                {"topic_key": "t:0:1", "skill_slugs": ["python", "unit-testing"]},
                {"topic_key": "t:0:2", "skill_slugs": ["python"]},
            ],
        }

    def test_apply_skill_graph_creates_skills_edges_and_mappings(self):
        from .models import PathSkill, Skill, SkillEdge
        from .skill_graph import apply_skill_graph

        result = apply_skill_graph(self.user, "path_test", self._graph())
        self.assertEqual(result["topics_mapped"], 3)
        self.assertEqual(Skill.objects.count(), 2)
        edge = SkillEdge.objects.get()
        self.assertEqual(edge.from_skill.slug, "python")
        self.assertEqual(edge.to_skill.slug, "unit-testing")
        self.assertEqual(PathSkill.objects.filter(user=self.user, path_id="path_test").count(), 4)

        # Re-applying replaces mappings without duplicating skills or edges.
        apply_skill_graph(self.user, "path_test", self._graph())
        self.assertEqual(Skill.objects.count(), 2)
        self.assertEqual(SkillEdge.objects.count(), 1)
        self.assertEqual(PathSkill.objects.filter(user=self.user, path_id="path_test").count(), 4)

    def test_apply_skill_graph_ignores_unknown_slugs(self):
        from .models import PathSkill, Skill
        from .skill_graph import apply_skill_graph

        graph = {
            "skills": [{"name": "Python", "slug": "python", "prerequisites": ["ghost"]}],
            "topic_map": [
                {"topic_key": "t:0:0", "skill_slugs": ["python", "ghost"]},
                {"topic_key": "bogus", "skill_slugs": ["python"]},
            ],
        }
        result = apply_skill_graph(self.user, "path_test", graph)
        self.assertEqual(Skill.objects.count(), 1)
        slugs = set(PathSkill.objects.filter(user=self.user).values_list("skill__slug", flat=True))
        self.assertEqual(slugs, {"python"})
        keys = set(PathSkill.objects.filter(user=self.user).values_list("topic_key", flat=True))
        self.assertEqual(keys, {"t:0:0", "bogus"})

    def test_record_skill_evidence_states_and_best_score(self):
        from .models import Skill, SkillMastery
        from .skill_graph import apply_skill_graph, record_skill_evidence

        apply_skill_graph(self.user, "path_test", self._graph())

        record_skill_evidence(self.user, "path_test", 0, 50, strong=False)
        m = SkillMastery.objects.get(user=self.user, skill__slug="python")
        self.assertEqual(m.state, SkillMastery.STATE_DEVELOPING)
        self.assertEqual(m.score, 50)

        record_skill_evidence(self.user, "path_test", 0, 85, strong=True)
        m.refresh_from_db()
        self.assertEqual(m.state, SkillMastery.STATE_VALIDATED)
        self.assertEqual(m.score, 85)
        self.assertEqual(m.evidence_count, 2)

        # Best score wins; weak evidence never downgrades validated mastery.
        record_skill_evidence(self.user, "path_test", 0, 40, strong=False)
        m.refresh_from_db()
        self.assertEqual(m.state, SkillMastery.STATE_VALIDATED)
        self.assertEqual(m.score, 85)
        self.assertEqual(m.evidence_count, 3)

    def test_record_evidence_only_touches_phase_skills(self):
        from .models import Skill, SkillMastery
        from .skill_graph import apply_skill_graph, record_skill_evidence

        graph = self._graph()
        graph["topic_map"].append({"topic_key": "t:1:0", "skill_slugs": ["unit-testing"]})
        apply_skill_graph(self.user, "path_test", graph)

        record_skill_evidence(self.user, "path_test", 1, 90, strong=True)
        self.assertTrue(
            SkillMastery.objects.filter(user=self.user, skill__slug="unit-testing", state="validated").exists()
        )
        self.assertFalse(
            SkillMastery.objects.filter(user=self.user, skill__slug="python").exists()
        )

    def test_extract_endpoint_returns_matrix(self):
        from unittest.mock import patch

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.skill_views.generate_skill_graph", return_value=self._graph()):
            resp = self.client.post(
                "/api/paths/path_test/skills/extract",
                data=json.dumps({}), content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["extracted"], 2)
        self.assertEqual(body["edges"], 1)
        self.assertEqual(body["topics_mapped"], 3)
        self.assertEqual(body["matrix"]["counts"]["unassessed"], 2)
        slugs = {s["slug"] for s in body["matrix"]["skills"]}
        self.assertEqual(slugs, {"python", "unit-testing"})

    def test_extract_rejects_invalid_graph_and_requires_login(self):
        from unittest.mock import patch

        resp = self.client.post(
            "/api/paths/path_test/skills/extract",
            data=json.dumps({}), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

        self._login()
        with patch("api.study_views._path_or_none", return_value=self.path), \
                patch("api.skill_views.generate_skill_graph", return_value={"skills": []}):
            resp = self.client.post(
                "/api/paths/path_test/skills/extract",
                data=json.dumps({}), content_type="application/json",
            )
        self.assertEqual(resp.status_code, 502)

    def test_matrix_endpoint_reports_states_and_edges(self):
        from unittest.mock import patch
        from .skill_graph import apply_skill_graph, record_skill_evidence

        self._login()
        graph = {
            "skills": [
                {"name": "Python", "slug": "python", "prerequisites": []},
                {"name": "Unit Testing", "slug": "unit-testing", "prerequisites": ["python"]},
            ],
            "topic_map": [
                {"topic_key": "t:0:0", "skill_slugs": ["python"]},
                {"topic_key": "t:1:0", "skill_slugs": ["unit-testing"]},
            ],
        }
        apply_skill_graph(self.user, "path_test", graph)
        record_skill_evidence(self.user, "path_test", 0, 88, strong=True)

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/skills/matrix")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        by_slug = {s["slug"]: s for s in body["skills"]}
        self.assertEqual(by_slug["python"]["state"], "validated")
        self.assertEqual(by_slug["python"]["score"], 88)
        self.assertEqual(by_slug["unit-testing"]["state"], "unassessed")
        self.assertEqual(body["counts"], {"unassessed": 1, "developing": 0, "validated": 1})
        self.assertEqual(body["edges"], [{"from": "python", "to": "unit-testing"}])
        self.assertIn("t:0:0", body["topic_map"])

    def test_recommendation_skips_topics_with_validated_skills(self):
        from unittest.mock import patch
        from .skill_graph import apply_skill_graph, record_skill_evidence

        self._login()
        graph = {
            "skills": [{"name": "Python", "slug": "python", "prerequisites": []}],
            "topic_map": [
                {"topic_key": "t:0:0", "skill_slugs": ["python"]},
                {"topic_key": "t:0:1", "skill_slugs": ["python"]},
            ],
        }
        apply_skill_graph(self.user, "path_test", graph)
        record_skill_evidence(self.user, "path_test", 0, 95, strong=True)

        with patch("api.study_views._path_or_none", return_value=self.path):
            resp = self.client.get("/api/paths/path_test/recommendation")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["state"], "learn")
        self.assertEqual(body["topic_key"], "t:0:2")
        self.assertIn("validated", body["reason"])


class ResourceCatalogTests(TestCase):
    """Curated resource catalog: upserts, health checks, search, generation hooks."""

    def setUp(self):
        self.user = User.objects.create_user(username="resuser", password="x")
        self.admin = User.objects.create_user(username="resadmin", password="x", is_superuser=True, is_staff=True)

    def _upsert(self, url="https://example.com/course", name="Example Course", **kw):
        from .resource_catalog import upsert_resource
        defaults = dict(type="course", level="beginner", cost="free", domain="web_development",
                        description="A test course", check_health=False)
        defaults.update(kw)
        return upsert_resource(url=url, name=name, **defaults)

    def test_upsert_dedupes_by_url(self):
        from .resource_catalog import upsert_resource
        from .models import Resource

        self._upsert(name="First")
        self._upsert(name="Second", duration_hours=12)
        row = Resource.objects.get()
        self.assertEqual(row.name, "Second")
        self.assertEqual(row.duration_hours, 12)

    def test_upsert_never_downgrades_curated_status(self):
        from .models import Resource

        row = self._upsert()
        row.content_source = "curated"
        row.save(update_fields=["content_source"])
        self._upsert(name="Reimported")
        row.refresh_from_db()
        self.assertEqual(row.content_source, "curated")

    def test_upsert_records_health_when_checked(self):
        from unittest.mock import patch
        from datetime import datetime, timezone as tz
        from .models import Resource

        fake = {"health": "ok", "final_url": "https://example.com/course", "status_code": 200}
        with patch("api.resource_catalog.check_url_health", return_value=fake):
            row = self._upsert(check_health=True)
        self.assertEqual(row.url_health, "ok")
        self.assertIsNotNone(row.verified_at)

    def test_stale_detection(self):
        from datetime import datetime, timedelta, timezone as tz
        from .resource_catalog import is_stale
        from .models import Resource

        row = self._upsert()
        self.assertTrue(is_stale(row))  # never verified

        row.verified_at = datetime.now(tz=tz.utc)
        row.url_health = "ok"
        self.assertFalse(is_stale(row))

        row.verified_at = datetime.now(tz=tz.utc) - timedelta(days=120)
        self.assertTrue(is_stale(row))

        row.verified_at = datetime.now(tz=tz.utc)
        row.url_health = "broken"
        self.assertTrue(is_stale(row))

    def test_search_catalog_orders_healthy_first_and_filters(self):
        from datetime import datetime, timedelta, timezone as tz
        from .resource_catalog import search_catalog
        from .models import Resource

        now = datetime.now(tz=tz.utc)
        broken = self._upsert(url="https://a.com", name="Broken Python Course")
        broken.url_health = "broken"
        broken.verified_at = now
        broken.save(update_fields=["url_health", "verified_at"])
        stale = self._upsert(url="https://b.com", name="Stale Python Course")
        stale.verified_at = now - timedelta(days=200)
        stale.url_health = "ok"
        stale.save(update_fields=["verified_at", "url_health"])
        fresh = self._upsert(url="https://c.com", name="Fresh Python Course", level="intermediate")
        fresh.url_health = "ok"
        fresh.verified_at = now
        fresh.save(update_fields=["url_health", "verified_at"])

        rows = search_catalog(query="Python")
        self.assertEqual([r.name for r in rows], ["Fresh Python Course", "Stale Python Course", "Broken Python Course"])

        rows = search_catalog(query="Python", difficulty="intermediate")
        self.assertEqual([r.name for r in rows], ["Fresh Python Course"])

    def test_search_endpoint_prefers_catalog(self):
        from unittest.mock import patch
        from .resource_catalog import upsert_resource

        fake = {"health": "ok", "final_url": "https://x.com", "status_code": 200}
        with patch("api.resource_catalog.check_url_health", return_value=fake):
            upsert_resource(url="https://x.com", name="Docker Deep Dive", type="course",
                            level="intermediate", cost="paid", domain="cloud_devops",
                            description="Containers from zero", check_health=True)

        resp = self.client.get("/api/resources/search?query=Docker")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["source"], "catalog")
        meta = body["results"][0]["metadata"]
        self.assertEqual(meta["topic_name"], "Docker Deep Dive")
        self.assertTrue(meta["verified"])
        self.assertEqual(meta["cost"], "paid")
        self.assertEqual(meta["source"], "catalog")

    def test_search_endpoint_falls_back_to_ai_labeled(self):
        from unittest.mock import patch
        from langchain_core.runnables import RunnableLambda

        payload = json.dumps([{
            "topic_name": "Suggested Topic", "domain": "data_science",
            "category": "course", "difficulty": "beginner",
            "estimated_hours": 10, "description": "from the model",
        }])
        with patch("api.views._cache_get", return_value=None), \
                patch("api.views._cache_set"), \
                patch("api.views._get_llm", return_value=RunnableLambda(lambda x: payload)):
            resp = self.client.get("/api/resources/search?query=nonexistent-xyz")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["source"], "ai")
        self.assertEqual(body["results"][0]["metadata"]["source"], "ai")
        self.assertFalse(body["results"][0]["metadata"]["verified"])

    def test_annotate_verified_resources(self):
        from .resource_catalog import annotate_verified_resources, catalog_index

        rows = [self._upsert(url="https://docs.python.org", name="Python Docs")]
        structured = {
            "phases": [
                {"topics": [
                    {"resources": [
                        {"name": "Python Docs", "type": "docs", "note": "official", "verified": True},
                        {"name": "Random Blog", "type": "article", "note": "ok", "verified": True},
                        {"name": "Other Course", "type": "course", "note": "fine", "verified": False},
                    ]},
                ]},
            ],
        }
        out = annotate_verified_resources(structured, catalog_index(rows))
        res = out["phases"][0]["topics"][0]["resources"]
        self.assertTrue(res[0]["verified"])
        self.assertEqual(res[0]["url"], "https://docs.python.org")
        self.assertEqual(res[0]["source"], "catalog")
        self.assertFalse(res[1]["verified"])  # claimed verified but not in catalog
        self.assertEqual(res[1]["source"], "ai")
        self.assertEqual(res[2]["source"], "ai")
        self.assertFalse(res[2]["verified"])

    def test_ingest_requires_admin_and_upserts(self):
        from unittest.mock import patch
        from .models import Resource

        payload = json.dumps({"query": "python"})
        resp = self.client.post("/api/resources/ingest", data=payload, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.user)
        resp = self.client.post("/api/resources/ingest", data=payload, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.admin)
        model_out = {"resources": [
            {"name": "Real Course", "url": "https://real.example/course", "type": "course",
             "level": "beginner", "cost": "free", "duration_hours": 20,
             "domain": "programming", "description": "Learn it"},
            {"name": "Bad", "url": "ftp://nope", "type": "course"},
        ]}
        fake = {"health": "ok", "final_url": "https://real.example/course", "status_code": 200}
        with patch("api.resource_views.generate_resource_ingest", return_value=model_out), \
                patch("api.resource_catalog.check_url_health", return_value=fake):
            resp = self.client.post("/api/resources/ingest", data=payload, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["created"], 1)
        self.assertEqual(body["skipped"], 1)
        row = Resource.objects.get()
        self.assertEqual(row.url_health, "ok")
        self.assertEqual(row.content_source, "ai_generated")

    def test_promote_and_verify_endpoints(self):
        from unittest.mock import patch
        from .resource_catalog import serialize_resource
        from .models import Resource

        row = self._upsert(url="https://p.example/x", name="Pick Me")
        self.client.force_login(self.admin)

        resp = self.client.post(
            f"/api/resources/{row.id}/promote",
            data=json.dumps({"content_source": "curated"}), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.content_source, "curated")

        fake = {"health": "redirect", "final_url": "https://p.example/y", "status_code": 200}
        with patch("api.resource_catalog.check_url_health", return_value=fake):
            resp = self.client.post(f"/api/resources/{row.id}/verify")
        self.assertEqual(resp.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.url_health, "redirect")
        self.assertEqual(row.final_url, "https://p.example/y")

    def test_path_structured_prefers_catalog_resources(self):
        from unittest.mock import patch
        from .resource_catalog import upsert_resource

        fake = {"health": "ok", "final_url": "https://docs.python.org", "status_code": 200}
        with patch("api.resource_catalog.check_url_health", return_value=fake):
            upsert_resource(url="https://docs.python.org", name="Python Docs", type="docs",
                            level="beginner", cost="free", domain="programming",
                            description="Official docs", check_health=True)

        generated = {
            "title": "Learn Python", "summary": "s", "total_weeks": 4,
            "phases": [{
                "title": "Basics", "description": "d", "estimated_weeks": 4,
                "topics": [{
                    "title": "Intro", "details": "x",
                    "resources": [
                        {"name": "Python Docs", "type": "docs", "note": "official", "verified": True},
                        {"name": "Made Up Blog", "type": "article", "note": "hmm", "verified": False},
                    ],
                }],
            }],
        }
        self.client.force_login(self.user)
        with patch("api.views.generate_learning_path_structured", return_value=generated), \
                patch("api.views.vector_memory") as memory, \
                patch("api.views.catalog_for_generation", return_value=[
                    type("R", (), {
                        "id": 1, "url": "https://docs.python.org", "name": "Python Docs",
                        "type": "docs", "level": "beginner", "cost": "free",
                        "duration_hours": None, "domain": "programming",
                        "description": "Official docs", "content_source": "curated",
                        "url_health": "ok", "final_url": "", "verified_at": now_tz(),
                        "community_rating": 4.5, "rating_count": 10,
                    })(),
                ]):
            memory.save_path.return_value = "path_new"
            resp = self.client.post(
                "/api/path/structured",
                data=json.dumps({"goal": "Learn Python"}), content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["id"], "path_new")
        out = body["output"]
        res = out["phases"][0]["topics"][0]["resources"]
        self.assertTrue(res[0]["verified"])
        self.assertEqual(res[0]["url"], "https://docs.python.org")
        self.assertEqual(res[0]["rating"], 4.5)
        self.assertFalse(res[1]["verified"])


def now_tz():
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc)


class AdaptivePlacementTests(TestCase):
    """One-question-at-a-time adaptive placement: engine unit tests and HTTP endpoints."""

    def _pool(self):
        return [
            {"id": "e1", "question": "Easy Q", "options": ["a", "b", "c", "d"], "answer_index": 0, "difficulty": "easy"},
            {"id": "m1", "question": "Med Q", "options": ["a", "b", "c", "d"], "answer_index": 1, "difficulty": "medium"},
            {"id": "h1", "question": "Hard Q", "options": ["a", "b", "c", "d"], "answer_index": 2, "difficulty": "hard"},
        ]

    # --- engine unit tests ---

    def test_correct_easy_advances_to_medium(self):
        from api.placement_adaptive import current_question, new_state, prepare_pool, record_answer
        pool = prepare_pool(self._pool())
        state = new_state("Python", pool)
        q = current_question(state)
        self.assertEqual(q["difficulty"], "easy")
        record_answer(state, q["id"], q["answer_index"])
        q2 = current_question(state)
        self.assertFalse(state["done"])
        self.assertEqual(q2["difficulty"], "medium")

    def test_miss_easy_stops_at_beginner(self):
        from api.placement_adaptive import current_question, new_state, prepare_pool, record_answer, session_summary
        pool = prepare_pool(self._pool())
        state = new_state("Python", pool)
        q = current_question(state)
        record_answer(state, q["id"], (q["answer_index"] + 1) % 4)  # wrong
        self.assertTrue(state["done"])
        self.assertEqual(state["level"], "beginner")
        summary = session_summary(state)
        self.assertEqual(summary["suggested_level"], "beginner")
        self.assertEqual(len(summary["missed"]), 1)

    def test_all_correct_reaches_advanced(self):
        from api.placement_adaptive import current_question, new_state, prepare_pool, record_answer
        pool = prepare_pool(self._pool())
        state = new_state("Python", pool)
        while not state["done"]:
            q = current_question(state)
            record_answer(state, q["id"], q["answer_index"])
        self.assertEqual(state["level"], "advanced")

    def test_miss_hard_gives_intermediate(self):
        from api.placement_adaptive import current_question, new_state, prepare_pool, record_answer
        pool = prepare_pool(self._pool())
        state = new_state("Python", pool)
        # answer easy and medium correctly
        for _ in range(2):
            q = current_question(state)
            record_answer(state, q["id"], q["answer_index"])
        # miss hard
        q = current_question(state)
        self.assertEqual(q["difficulty"], "hard")
        record_answer(state, q["id"], (q["answer_index"] + 1) % 4)
        self.assertTrue(state["done"])
        self.assertEqual(state["level"], "intermediate")

    def test_duplicate_answer_raises(self):
        from api.placement_adaptive import current_question, new_state, prepare_pool, record_answer
        pool = prepare_pool(self._pool())
        state = new_state("Python", pool)
        q = current_question(state)
        record_answer(state, q["id"], q["answer_index"])
        with self.assertRaises(ValueError):
            record_answer(state, q["id"], 0)

    def test_unknown_question_id_raises(self):
        from api.placement_adaptive import new_state, prepare_pool, record_answer
        pool = prepare_pool(self._pool())
        state = new_state("Python", pool)
        with self.assertRaises(KeyError):
            record_answer(state, "ghost", 0)

    def test_pool_without_hard_band_finishes_at_advanced(self):
        """If the LLM omits hard questions, completing easy+medium still reaches advanced."""
        from api.placement_adaptive import current_question, new_state, prepare_pool, record_answer
        pool = prepare_pool([
            {"id": "e1", "question": "Q", "options": ["a", "b"], "answer_index": 0, "difficulty": "easy"},
            {"id": "m1", "question": "Q", "options": ["a", "b"], "answer_index": 0, "difficulty": "medium"},
        ])
        state = new_state("Python", pool)
        while not state["done"]:
            q = current_question(state)
            record_answer(state, q["id"], q["answer_index"])
        self.assertEqual(state["level"], "advanced")

    # --- HTTP endpoint tests ---

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def test_adaptive_start_returns_first_question(self):
        from unittest.mock import patch
        from api.placement_adaptive import prepare_pool

        with patch("api.views.generate_placement_quiz", return_value={"questions": self._pool()}):
            resp = self._post("/api/placement/adaptive/start", {"goal": "Python"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("session_id", body)
        self.assertFalse(body["done"])
        self.assertIn("question", body)
        self.assertNotIn("answer_index", body["question"])  # answer must not leak

    def test_adaptive_answer_advances_and_finishes(self):
        from unittest.mock import patch

        with patch("api.views.generate_placement_quiz", return_value={"questions": self._pool()}):
            start = self._post("/api/placement/adaptive/start", {"goal": "Python"}).json()

        session_id = start["session_id"]
        # Answer all questions correctly by reading the session state directly.
        # We can't read answer_index from the response (it's stripped), so we
        # drive through the engine by always picking index 0 and accepting whatever level results.
        resp = None
        for _ in range(5):  # at most 3 questions in our pool
            q = (resp or start)["question"]
            resp = self._post("/api/placement/adaptive/answer", {
                "session_id": session_id,
                "question_id": q["id"],
                "answer_index": 0,
            }).json()
            if resp.get("done"):
                break
        self.assertTrue(resp["done"])
        self.assertIn("summary", resp)
        self.assertIn(resp["summary"]["suggested_level"], ("beginner", "intermediate", "advanced"))

    def test_adaptive_answer_unknown_session_is_404(self):
        resp = self._post("/api/placement/adaptive/answer", {
            "session_id": "ghost", "question_id": "q1", "answer_index": 0,
        })
        self.assertEqual(resp.status_code, 404)

    def test_adaptive_start_requires_goal(self):
        resp = self._post("/api/placement/adaptive/start", {})
        self.assertEqual(resp.status_code, 400)


class AnalyticsEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analyst", password="x")
        self.path = structured_path(owner=str(self.user.id))
        self.path_doc = {
            "id": "path_test",
            "content": self.path["content"],
            "metadata": self.path["metadata"],
        }

    def _login(self):
        self.client.force_login(self.user)

    def _mock_path(self):
        from unittest.mock import patch

        patcher = patch("api.views.vector_memory")
        self.addCleanup(patcher.stop)
        memory = patcher.start()
        memory.get_path.return_value = self.path_doc
        return memory

    def test_all_endpoints_require_login(self):
        for url in (
            "/api/analytics/dashboard/path_test",
            "/api/analytics/daily/path_test",
            "/api/analytics/velocity/path_test",
            "/api/analytics/cohort/path_test",
        ):
            self.assertEqual(self.client.get(url).status_code, 401, url)

    def test_missing_path_is_404(self):
        from unittest.mock import patch

        self._login()
        with patch("api.views.vector_memory") as memory:
            memory.get_path.return_value = None
            self.assertEqual(
                self.client.get("/api/analytics/dashboard/nope").status_code, 404
            )

    def test_dashboard_counts_topics_time_scores_and_weak_areas(self):
        from .models import FocusSession, LearningAnalytics

        self._login()
        PathProgress.objects.create(user=self.user, path_id="path_test", item_key="t:0:0", done=True)
        PathProgress.objects.create(user=self.user, path_id="path_test", item_key="t:0:1", done=True)
        PathProgress.objects.create(user=self.user, path_id="path_test", item_key="t:0:2", done=False)
        TestResult.objects.create(user=self.user, path_id="path_test", phase_idx=0, score=4, total=5, percent=80)
        TestResult.objects.create(user=self.user, path_id="path_test", phase_idx=1, score=2, total=5, percent=40)
        FocusSession.objects.create(user=self.user, path_id="path_test", phase_idx=0, seconds=3600)

        with self._mock_path():
            data = self.client.get("/api/analytics/dashboard/path_test").json()

        self.assertEqual(data["topics_completed"], 2)
        self.assertEqual(data["topics_total"], 5)  # 3 + 2 topics; phases not double-counted
        self.assertEqual(data["total_time_minutes"], 60)
        self.assertEqual(data["average_test_score"], 60.0)
        self.assertEqual(data["days_active"], 1)
        self.assertIsNotNone(data["last_activity"])
        self.assertEqual(data["predicted_completion_days"], 1)
        # Phase 1 ("Advanced") averaged 40% < 70% threshold
        self.assertEqual(len(data["weak_areas"]), 1)
        self.assertEqual(data["weak_areas"][0]["phase"], "Advanced")
        self.assertEqual(data["weak_areas"][0]["avg_score"], 40.0)
        self.assertTrue(
            LearningAnalytics.objects.filter(user=self.user, path_id="path_test").exists()
        )

    def test_daily_metrics_is_zero_filled_for_30_days(self):
        from django.utils import timezone as tz

        from .models import FocusSession

        self._login()
        FocusSession.objects.create(user=self.user, path_id="path_test", seconds=1800)

        with self._mock_path():
            data = self.client.get("/api/analytics/daily/path_test").json()

        metrics = data["metrics"]
        self.assertEqual(len(metrics), 30)
        self.assertEqual(metrics[0]["time_minutes"], 0)
        self.assertEqual(metrics[-1]["date"], tz.now().date().isoformat())
        self.assertEqual(metrics[-1]["time_minutes"], 30)
        self.assertEqual(metrics[-1]["topics_completed"], 0)
        self.assertEqual(metrics[-1]["tests_taken"], 0)

    def test_cohort_comparison_averages_and_percentile(self):
        from .models import FocusSession

        peer = User.objects.create_user(username="peer", password="x")
        FocusSession.objects.create(user=self.user, path_id="path_test", seconds=1800)  # 30 min
        FocusSession.objects.create(user=peer, path_id="path_test", seconds=3600)  # 60 min
        PathProgress.objects.create(user=peer, path_id="path_test", item_key="t:0:0", done=True)

        self._login()
        with self._mock_path():
            data = self.client.get("/api/analytics/cohort/path_test").json()

        self.assertEqual(data["user_time_minutes"], 30)
        self.assertEqual(data["cohort_avg_time_minutes"], 45.0)
        self.assertEqual(data["user_topics_completed"], 0)
        self.assertEqual(data["cohort_avg_topics"], 0.5)
        self.assertEqual(data["cohort_size"], 2)
        self.assertEqual(data["percentile"], 0)  # below the peer

    def test_velocity_uses_last_week_progress(self):
        self._login()
        PathProgress.objects.create(user=self.user, path_id="path_test", item_key="t:0:0", done=True)
        PathProgress.objects.create(user=self.user, path_id="path_test", item_key="t:0:1", done=True)
        PathProgress.objects.create(user=self.user, path_id="path_test", item_key="t:0:2", done=False)

        with self._mock_path():
            data = self.client.get("/api/analytics/velocity/path_test").json()

        self.assertEqual(data["topics_per_week"], 2)
        self.assertEqual(data["estimated_completion_weeks"], 1)  # 1 remaining / 2 this week


class SkillGraphViewTests(TestCase):
    def setUp(self):
        from .skill_graph import apply_skill_graph

        self.user = User.objects.create_user(username="grapher", password="x")
        self.path = structured_path(owner=str(self.user.id))
        self.path_doc = {
            "id": "path_test",
            "content": self.path["content"],
            "metadata": self.path["metadata"],
        }
        # Two skills, one prerequisite edge (Python -> Decorators),
        # mapped to phase 0 and phase 1 topics.
        graph = {
            "skills": [
                {"name": "Python", "slug": "python", "description": "core", "domain": "programming",
                 "prerequisites": []},
                {"name": "Decorators", "slug": "decorators", "description": "wrap", "domain": "programming",
                 "prerequisites": ["python"]},
            ],
            "topic_map": [
                {"topic_key": "t:0:0", "skill_slugs": ["python"]},
                {"topic_key": "t:1:0", "skill_slugs": ["decorators"]},
            ],
        }
        apply_skill_graph(
            self.user, "path_test", graph,
            topic_titles={"t:0:0": "Variables", "t:1:0": "Decorators"},
        )

    def _login(self):
        self.client.force_login(self.user)

    def _mock_path(self):
        from unittest.mock import patch

        patcher = patch("api.views.vector_memory")
        self.addCleanup(patcher.stop)
        memory = patcher.start()
        memory.get_path.return_value = self.path_doc
        return memory

    def test_graph_requires_login(self):
        self.assertEqual(self.client.get("/api/skills/graph/path_test").status_code, 401)
        self.assertEqual(self.client.get("/api/skills/blockers/path_test").status_code, 401)
        self.assertEqual(self.client.get("/api/skills/critical-path/path_test").status_code, 401)
        self.assertEqual(self.client.get("/api/skills/mastery").status_code, 401)
        self.assertEqual(self.client.get("/api/skills/1/prerequisites").status_code, 401)
        self.assertEqual(self.client.get("/api/skills/1/unlocks").status_code, 401)

    def test_graph_returns_deduped_nodes_and_real_edges(self):
        self._login()
        with self._mock_path():
            data = self.client.get("/api/skills/graph/path_test").json()

        self.assertEqual(len(data["nodes"]), 2)
        ids = [n["id"] for n in data["nodes"]]
        self.assertEqual(len(ids), len(set(ids)), "nodes must be unique")
        by_name = {n["name"]: n for n in data["nodes"]}
        self.assertEqual(by_name["Python"]["phase"], 0)
        self.assertEqual(by_name["Decorators"]["phase"], 1)
        self.assertEqual(by_name["Python"]["topics"], ["Variables"])
        self.assertEqual(
            data["edges"], [{"from": by_name["Python"]["id"], "to": by_name["Decorators"]["id"]}]
        )

    def test_prerequisites_and_unlocks_use_skilledge(self):
        from .models import Skill

        self._login()
        python_id = Skill.objects.get(slug="python").id
        decorators_id = Skill.objects.get(slug="decorators").id

        prereqs = self.client.get(f"/api/skills/{decorators_id}/prerequisites").json()
        self.assertEqual([p["id"] for p in prereqs["prerequisites"]], [python_id])

        unlocks = self.client.get(f"/api/skills/{python_id}/unlocks").json()
        self.assertEqual([u["id"] for u in unlocks["unlocks"]], [decorators_id])

    def test_unknown_skill_is_404(self):
        self._login()
        self.assertEqual(self.client.get("/api/skills/999999/prerequisites").status_code, 404)
        self.assertEqual(self.client.get("/api/skills/999999/unlocks").status_code, 404)

    def test_critical_path_lists_skills_with_dependents(self):
        from .models import Skill

        self._login()
        with self._mock_path():
            data = self.client.get("/api/skills/critical-path/path_test").json()

        self.assertEqual(data["total_critical"], 1)
        entry = data["critical_skills"][0]
        self.assertEqual(entry["skill"], "Python")
        self.assertEqual(entry["unlocks_count"], 1)
        self.assertEqual(entry["prerequisite_count"], 0)
        self.assertEqual(entry["skill_id"], Skill.objects.get(slug="python").id)

    def test_phase_blockers_flags_cross_phase_prerequisite(self):
        self._login()
        with self._mock_path():
            data = self.client.get("/api/skills/blockers/path_test").json()

        # Decorators (phase 1) requires Python (phase 0) — normal order, no warning.
        self.assertEqual(data["warnings"], [])

    def test_phase_blockers_flags_missing_prerequisite(self):
        from .models import PathSkill, Skill

        # A path that maps only Decorators (Python edge exists globally but is
        # not part of this path) -> missing-prerequisite warning.
        PathSkill.objects.filter(
            user=self.user, path_id="path_test", skill__slug="python"
        ).delete()

        self._login()
        with self._mock_path():
            data = self.client.get("/api/skills/blockers/path_test").json()

        self.assertEqual(len(data["warnings"]), 1)
        warning = data["warnings"][0]
        self.assertEqual(warning["type"], "missing_prerequisite")
        self.assertIn("not covered in this path", warning["message"])

    def test_mastery_status_returns_real_rows(self):
        from .skill_graph import record_skill_evidence
        from .models import Skill

        record_skill_evidence(self.user, "path_test", phase_idx=0, score=85, strong=True)
        self._login()
        data = self.client.get("/api/skills/mastery").json()

        self.assertEqual(len(data["mastery"]), 1)
        entry = data["mastery"][0]
        self.assertEqual(entry["skill"], "Python")
        self.assertEqual(entry["state"], "validated")
        self.assertEqual(entry["score"], 85)


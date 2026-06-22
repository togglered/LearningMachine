from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.attempts import services
from apps.attempts.models import Attempt
from apps.content.models import (
    Question,
    Section,
    SectionType,
    Subject,
    TaskGroup,
    Test,
)
from apps.users.models import User


class AttemptServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="u", password="p")
        self.subject = Subject.objects.create(name="IELTS", slug="ielts")
        self.test = Test.objects.create(
            subject=self.subject, time_limit=timedelta(minutes=30)
        )
        st = SectionType.objects.create(subject=self.subject, name="Listening")
        section = Section.objects.create(test=self.test, section_type=st, position=0)
        tg = TaskGroup.objects.create(section=section, position=0)
        self.q = Question.objects.create(
            task_group=tg,
            kind=Question.Kind.SINGLE_CHOICE,
            prompt="?",
            content={"options": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]},
            answer_key={"correct": "a"},
            points=Decimal("2"),
        )

    def test_default_time_applies_snapshot(self) -> None:
        a = services.start_attempt(self.user, self.test, use_default_time=True)
        self.assertEqual(a.time_limit, timedelta(minutes=30))

    def test_no_timer_when_unchecked(self) -> None:
        a = services.start_attempt(self.user, self.test, use_default_time=False)
        self.assertIsNone(a.time_limit)

    def test_scoring(self) -> None:
        a = services.start_attempt(self.user, self.test, use_default_time=False)
        services.save_answer(a, self.q, "a")
        services.finish_attempt(a)
        a.refresh_from_db()
        self.assertEqual(a.status, Attempt.Status.SUBMITTED)
        self.assertEqual(a.score, Decimal("2"))

    def test_save_answer_on_expired_persists_status(self) -> None:
        a = services.start_attempt(self.user, self.test, use_default_time=True)
        Attempt.objects.filter(pk=a.pk).update(
            started_at=timezone.now() - timedelta(hours=2)
        )
        a.refresh_from_db()
        with self.assertRaises(ValueError):
            services.save_answer(a, self.q, "a")
        a.refresh_from_db()
        self.assertEqual(a.status, Attempt.Status.EXPIRED)

    from rest_framework.test import APITestCase


class AttemptApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_authenticate(self.user)
        subject = Subject.objects.create(name="IELTS", slug="ielts")
        self.test = Test.objects.create(subject=subject, is_published=True)
        st = SectionType.objects.create(subject=subject, name="Listening")
        section = Section.objects.create(test=self.test, section_type=st, position=0)
        tg = TaskGroup.objects.create(section=section, position=0)
        self.q = Question.objects.create(
            task_group=tg,
            kind=Question.Kind.SINGLE_CHOICE,
            prompt="?",
            content={"options": [{"id": "a", "text": "x"}]},
            answer_key={"correct": "a"},
            points=Decimal("2"),
        )

    def test_full_flow(self) -> None:
        r = self.client.post(
            "/api/v1/attempts/",
            {"test": self.test.id, "use_default_time": False},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        aid = r.json()["id"]
        r = self.client.post(
            f"/api/v1/attempts/{aid}/answers/",
            {"question": self.q.id, "response": "a"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        r = self.client.post(f"/api/v1/attempts/{aid}/finish/")
        self.assertEqual(r.json()["status"], "submitted")
        self.assertEqual(r.json()["score"], "2.00")

    def test_cannot_access_foreign_attempt(self) -> None:
        other = User.objects.create_user(username="o", password="p")
        attempt = services.start_attempt(other, self.test, use_default_time=False)
        r = self.client.get(f"/api/v1/attempts/{attempt.id}/")
        self.assertEqual(r.status_code, 404)

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

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

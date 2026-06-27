from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APITestCase

from apps.content import grading
from apps.content.grading import Grader
from apps.content.models import (
    Question,
    Section,
    SectionType,
    Subject,
    TaskGroup,
    Test,
)
from apps.users.models import User


class SingleChoiceGraderTests(SimpleTestCase):
    def setUp(self) -> None:
        grader = grading.get_grader(Question.Kind.SINGLE_CHOICE)
        assert grader is not None
        self.grader: Grader = grader
        self.content = {"options": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]}

    def test_valid_passes(self) -> None:
        self.grader.validate(self.content, {"correct": "a"})

    def test_correct_must_exist(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate(self.content, {"correct": "z"})

    def test_is_correct(self) -> None:
        self.assertTrue(self.grader.is_correct({"correct": "a"}, "a"))
        self.assertFalse(self.grader.is_correct({"correct": "a"}, "b"))


class MultiChoiceGraderTests(SimpleTestCase):
    def setUp(self) -> None:
        grader = grading.get_grader(Question.Kind.MULTI_CHOICE)
        assert grader is not None
        self.grader: Grader = grader

    def test_order_independent(self) -> None:
        self.assertTrue(self.grader.is_correct({"correct": ["a", "b"]}, ["b", "a"]))


class QuestionCleanTests(TestCase):
    def test_clean_rejects_bad_answer_key(self) -> None:
        subject = Subject.objects.create(name="IELTS", slug="ielts")
        test = Test.objects.create(subject=subject)
        st = SectionType.objects.create(subject=subject, name="Listening")
        section = Section.objects.create(test=test, section_type=st, position=0)
        tg = TaskGroup.objects.create(section=section, position=0)
        q = Question(
            task_group=tg,
            kind=Question.Kind.SINGLE_CHOICE,
            prompt="?",
            content={"options": [{"id": "a", "text": "x"}]},
            answer_key={"correct": "z"},
        )
        with self.assertRaises(ValidationError):
            q.full_clean()


class TestApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_authenticate(self.user)
        subject = Subject.objects.create(name="IELTS", slug="ielts")
        self.test = Test.objects.create(subject=subject, is_published=True)
        st = SectionType.objects.create(subject=subject, name="Listening")
        section = Section.objects.create(test=self.test, section_type=st, position=0)
        tg = TaskGroup.objects.create(section=section, position=0)
        Question.objects.create(
            task_group=tg,
            kind=Question.Kind.SINGLE_CHOICE,
            prompt="?",
            content={"options": [{"id": "a", "text": "x"}]},
            answer_key={"correct": "a"},
        )

    def test_detail_hides_answer_key(self) -> None:
        resp = self.client.get(f"/api/v1/tests/{self.test.id}/")
        self.assertEqual(resp.status_code, 200)
        q = resp.json()["sections"][0]["task_groups"][0]["questions"][0]
        self.assertNotIn("answer_key", q)

    def test_requires_auth(self) -> None:
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/tests/").status_code, 401)


class SchemaTests(APITestCase):
    def test_schema_available(self) -> None:
        self.assertEqual(self.client.get("/api/v1/schema/").status_code, 200)


class GapFillGraderTests(SimpleTestCase):
    def setUp(self) -> None:
        grader = grading.get_grader(Question.Kind.GAP_FILL)
        assert grader is not None
        self.grader: Grader = grader
        self.content = {
            "text": "The {{1}} fox over the {{2}} dog",
            "gaps": [{"id": "1"}, {"id": "2"}],
        }
        self.answer_key = {"answers": {"1": ["quick", "fast"], "2": ["lazy"]}}

    def test_valid_passes(self) -> None:
        self.grader.validate(self.content, self.answer_key)

    def test_answer_keys_must_match_gaps(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate(self.content, {"answers": {"1": ["quick"]}})

    def test_is_correct(self) -> None:
        self.assertTrue(
            self.grader.is_correct(self.answer_key, {"1": "quick", "2": "lazy"})
        )
        self.assertTrue(
            self.grader.is_correct(self.answer_key, {"1": " FAST ", "2": "lazy"})
        )
        self.assertFalse(
            self.grader.is_correct(self.answer_key, {"1": "slow", "2": "lazy"})
        )
        self.assertFalse(self.grader.is_correct(self.answer_key, {"1": "quick"}))


class MatchingGraderTests(SimpleTestCase):
    def setUp(self) -> None:
        grader = grading.get_grader(Question.Kind.MATCHING)
        assert grader is not None
        self.grader: Grader = grader
        self.content = {
            "left": [{"id": "l1", "text": "Dog"}, {"id": "l2", "text": "Cat"}],
            "right": [{"id": "r1", "text": "Barks"}, {"id": "r2", "text": "Meows"}],
        }
        self.answer_key = {"pairs": {"l1": "r1", "l2": "r2"}}

    def test_valid_passes(self) -> None:
        self.grader.validate(self.content, self.answer_key)

    def test_pairs_must_cover_left(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate(self.content, {"pairs": {"l1": "r1"}})

    def test_unknown_right_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate(self.content, {"pairs": {"l1": "rX", "l2": "r2"}})

    def test_is_correct(self) -> None:
        self.assertTrue(
            self.grader.is_correct(self.answer_key, {"l1": "r1", "l2": "r2"})
        )
        self.assertFalse(
            self.grader.is_correct(self.answer_key, {"l1": "r2", "l2": "r1"})
        )

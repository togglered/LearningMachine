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

    def test_valid_passes(self) -> None:
        content = {"options": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]}
        self.grader.validate(content, {"correct": ["a", "b"]})

    def test_correct_must_be_non_empty_list(self) -> None:
        content = {"options": [{"id": "a", "text": "x"}]}
        with self.assertRaises(ValidationError):
            self.grader.validate(content, {"correct": []})
        with self.assertRaises(ValidationError):
            self.grader.validate(content, {"correct": "a"})

    def test_unknown_ids_rejected(self) -> None:
        content = {"options": [{"id": "a", "text": "x"}]}
        with self.assertRaises(ValidationError):
            self.grader.validate(content, {"correct": ["a", "z"]})

    def test_is_correct_negatives(self) -> None:
        key = {"correct": ["a", "b"]}
        self.assertFalse(self.grader.is_correct(key, ["a"]))
        self.assertFalse(self.grader.is_correct(key, ["a", "b", "c"]))
        self.assertFalse(self.grader.is_correct(key, "a"))
        self.assertFalse(self.grader.is_correct(key, []))


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


class ShortAnswerGraderTests(SimpleTestCase):
    def setUp(self) -> None:
        grader = grading.get_grader(Question.Kind.SHORT_ANSWER)
        assert grader is not None
        self.grader: Grader = grader
        self.answer_key = {"accepted": ["colour", "color"]}

    def test_valid_passes(self) -> None:
        self.grader.validate({}, self.answer_key)

    def test_accepted_must_be_non_empty_list_of_str(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate({}, {"accepted": []})
        with self.assertRaises(ValidationError):
            self.grader.validate({}, {"accepted": [1, 2]})

    def test_is_correct_normalizes(self) -> None:
        self.assertTrue(self.grader.is_correct(self.answer_key, "colour"))
        self.assertTrue(self.grader.is_correct(self.answer_key, "  COLOR "))
        self.assertFalse(self.grader.is_correct(self.answer_key, "colur"))
        self.assertFalse(self.grader.is_correct(self.answer_key, 123))


class EssayGraderTests(SimpleTestCase):
    def setUp(self) -> None:
        grader = grading.get_grader(Question.Kind.ESSAY)
        assert grader is not None
        self.grader: Grader = grader
        self.content = {
            "criteria": [
                {"id": "task", "text": "Task response", "points": 9},
                {"id": "coherence", "text": "Coherence", "points": 9},
            ]
        }

    def test_valid_passes(self) -> None:
        self.grader.validate(self.content, {})

    def test_criteria_required(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate({"criteria": []}, {})

    def test_missing_fields_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate({"criteria": [{"id": "a", "text": "x"}]}, {})

    def test_points_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate(
                {"criteria": [{"id": "a", "text": "x", "points": 0}]}, {}
            )

    def test_duplicate_ids_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.grader.validate(
                {
                    "criteria": [
                        {"id": "a", "text": "x", "points": 1},
                        {"id": "a", "text": "y", "points": 1},
                    ]
                },
                {},
            )

    def test_not_auto_gradable(self) -> None:
        self.assertFalse(self.grader.auto_gradable)
        self.assertFalse(self.grader.is_correct({}, "any essay text"))

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

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

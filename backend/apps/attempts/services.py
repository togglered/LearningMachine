from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.content.grading import get_grader
from apps.content.models import Question, Test
from apps.users.models import User

from .models import Answer, Attempt


def _ensure_question_in_attempt(attempt: Attempt, question: Question) -> None:
    if question.task_group.section.test_id != attempt.test_id:
        raise ValueError("Question does not belong to this attempt.")


def start_attempt(user: User, test: Test, *, use_default_time: bool) -> Attempt:
    return Attempt.objects.create(
        user=user,
        test=test,
        time_limit=test.time_limit if use_default_time else None,
    )


def save_answer(attempt: Attempt, question: Question, response: Any) -> Answer:
    _ensure_question_in_attempt(attempt, question)
    if attempt.status != Attempt.Status.IN_PROGRESS:
        raise ValueError("Attempt is not in progress.")
    if attempt.is_expired:
        attempt.status = Attempt.Status.EXPIRED
        attempt.save(update_fields=["status"])
        raise ValueError("Attempt time is up.")
    answer, _ = Answer.objects.update_or_create(
        attempt=attempt, question=question, defaults={"response": response}
    )
    return answer


@transaction.atomic
def finish_attempt(attempt: Attempt) -> Attempt:
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return attempt
    total = Decimal("0")
    for answer in attempt.answers.select_related("question"):
        q = answer.question
        grader = get_grader(q.kind)
        if grader is None:
            continue
        correct = grader.is_correct(q.answer_key, answer.response)
        answer.is_correct = correct
        answer.awarded_points = q.points if correct else Decimal("0")
        answer.save(update_fields=["is_correct", "awarded_points"])
        if correct:
            total += q.points
    attempt.score = total
    attempt.status = (
        Attempt.Status.EXPIRED if attempt.is_expired else Attempt.Status.SUBMITTED
    )
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["score", "status", "submitted_at"])
    return attempt

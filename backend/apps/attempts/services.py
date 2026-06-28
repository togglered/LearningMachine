from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
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
        if grader is None or not grader.auto_gradable:
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


@transaction.atomic
def self_assess(attempt: Attempt, question: Question, scores: dict[str, Any]) -> Answer:
    _ensure_question_in_attempt(attempt, question)
    if attempt.status != Attempt.Status.SUBMITTED:
        raise ValueError("Attempt is not submitted.")
    if question.kind != Question.Kind.ESSAY:
        raise ValueError("Self-assessment is only for essay questions.")
    max_by_id = {
        str(c["id"]): c["points"] for c in question.content.get("criteria", [])
    }
    total = Decimal("0")
    for cid, pts in scores.items():
        max_pts = max_by_id.get(str(cid))
        if max_pts is None:
            raise ValueError(f"Unknown criterion: {cid}")
        if not isinstance(pts, int | float) or pts < 0 or pts > max_pts:
            raise ValueError(f"Invalid points for criterion {cid}.")
        total += Decimal(str(pts))
    max_total = sum((Decimal(str(p)) for p in max_by_id.values()), Decimal("0"))
    answer, _ = attempt.answers.update_or_create(
        question=question,
        defaults={"awarded_points": total, "is_correct": total >= max_total},
    )
    attempt.score = attempt.answers.aggregate(s=Sum("awarded_points"))["s"] or Decimal(
        "0"
    )
    attempt.save(update_fields=["score"])
    return answer

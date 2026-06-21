from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Attempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="attempts", on_delete=models.CASCADE
    )
    test = models.ForeignKey(
        "content.Test", related_name="attempts", on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    started_at = models.DateTimeField(auto_now_add=True)
    time_limit = models.DurationField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.user} · {self.test} · {self.status}"

    @property
    def deadline(self) -> datetime | None:
        if self.time_limit is None:
            return None
        return self.started_at + self.time_limit

    @property
    def is_expired(self) -> bool:
        return self.deadline is not None and timezone.now() > self.deadline


class Answer(TimeStampedModel):
    attempt = models.ForeignKey(
        Attempt, related_name="answers", on_delete=models.CASCADE
    )
    question = models.ForeignKey("content.Question", on_delete=models.PROTECT)
    response = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(null=True)
    awarded_points = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"], name="uniq_answer_per_question"
            ),
        ]

    def __str__(self) -> str:
        return f"attempt {self.attempt_id} · q{self.question_id}"

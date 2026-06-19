from django.db import models

from apps.core.models import TimeStampedModel


class Subject(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Test(TimeStampedModel):
    subject = models.ForeignKey(Subject, related_name="tests", on_delete=models.PROTECT)
    is_published = models.BooleanField(default=False)
    time_limit = models.DurationField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.subject} — test #{self.pk}"


class SectionType(TimeStampedModel):
    subject = models.ForeignKey(
        Subject, related_name="section_types", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "name"], name="uniq_sectiontype_per_subject"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject}: {self.name}"


class Section(TimeStampedModel):
    test = models.ForeignKey(Test, related_name="sections", on_delete=models.CASCADE)
    section_type = models.ForeignKey(
        SectionType, related_name="sections", on_delete=models.PROTECT
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "position"], name="uniq_section_position"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.test} / {self.section_type.name}"


class TaskGroup(TimeStampedModel):
    section = models.ForeignKey(
        Section, related_name="task_groups", on_delete=models.CASCADE
    )
    instructions = models.TextField(blank=True)
    passage = models.TextField(blank=True)
    audio = models.FileField(upload_to="task_groups/audio/", null=True, blank=True)
    image = models.ImageField(upload_to="task_groups/img/", null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return self.section.section_type.name or f"Task group #{self.pk}"


class Question(TimeStampedModel):
    class Kind(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Single choice"
        MULTI_CHOICE = "multi_choice", "Multiple choice"
        GAP_FILL = "gap_fill", "Gap fill"
        MATCHING = "matching", "Matching"
        SHORT_ANSWER = "short_answer", "Short answer"
        ESSAY = "essay", "Essay"

    task_group = models.ForeignKey(
        TaskGroup, related_name="questions", on_delete=models.CASCADE
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    prompt = models.TextField()
    content = models.JSONField(default=dict, blank=True)
    answer_key = models.JSONField(default=dict, blank=True)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    explanation = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return f"[{self.get_kind_display()}] {self.prompt[:50]}"

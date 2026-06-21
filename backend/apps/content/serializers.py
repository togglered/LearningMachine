from rest_framework import serializers

from .models import Question, Section, SectionType, TaskGroup, Test


class QuestionSerializer(serializers.ModelSerializer[Question]):
    class Meta:
        model = Question
        fields = ["id", "kind", "prompt", "content", "points", "position"]


class TaskGroupSerializer(serializers.ModelSerializer[TaskGroup]):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TaskGroup
        fields = [
            "id",
            "instructions",
            "passage",
            "audio",
            "image",
            "position",
            "questions",
        ]


class SectionSerializer(serializers.ModelSerializer[Section]):
    section_type: serializers.StringRelatedField[SectionType] = (
        serializers.StringRelatedField()
    )
    task_groups = TaskGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ["id", "section_type", "position", "task_groups"]


class TestListSerializer(serializers.ModelSerializer[Test]):
    class Meta:
        model = Test
        fields = ["id", "subject", "time_limit", "is_published"]


class TestDetailSerializer(serializers.ModelSerializer[Test]):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = ["id", "subject", "time_limit", "sections"]

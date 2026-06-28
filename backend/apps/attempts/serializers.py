from typing import Any

from rest_framework import serializers

from apps.content.models import Question, Test

from .models import Answer, Attempt


class StartAttemptSerializer(serializers.Serializer[Any]):
    test: serializers.PrimaryKeyRelatedField[Test] = serializers.PrimaryKeyRelatedField(
        queryset=Test.objects.filter(is_published=True)
    )
    use_default_time = serializers.BooleanField(default=True)


class SaveAnswerSerializer(serializers.Serializer[Any]):
    question: serializers.PrimaryKeyRelatedField[Question] = (
        serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    )
    response = serializers.JSONField()


class AnswerSerializer(serializers.ModelSerializer[Answer]):
    class Meta:
        model = Answer
        fields = ["id", "question", "response", "is_correct", "awarded_points"]


class AttemptSerializer(serializers.ModelSerializer[Attempt]):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "test",
            "status",
            "started_at",
            "time_limit",
            "submitted_at",
            "score",
            "answers",
        ]


class SelfAssessSerializer(serializers.Serializer[Any]):
    question: serializers.PrimaryKeyRelatedField[Question] = (
        serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    )
    scores = serializers.DictField(child=serializers.FloatField())

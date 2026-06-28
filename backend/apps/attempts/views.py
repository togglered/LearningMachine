from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.models import User

from . import services
from .models import Attempt
from .serializers import (
    AttemptSerializer,
    SaveAnswerSerializer,
    SelfAssessSerializer,
    StartAttemptSerializer,
)


class AttemptViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet[Attempt],
):
    serializer_class = AttemptSerializer

    def get_queryset(self) -> QuerySet[Attempt]:
        if getattr(self, "swagger_fake_view", False):
            return Attempt.objects.none()
        assert isinstance(self.request.user, User)
        return Attempt.objects.filter(user=self.request.user).prefetch_related(
            "answers"
        )

    @extend_schema(request=StartAttemptSerializer, responses=AttemptSerializer)
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ser = StartAttemptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        assert isinstance(user, User)
        attempt = services.start_attempt(
            user,
            ser.validated_data["test"],
            use_default_time=ser.validated_data["use_default_time"],
        )
        return Response(AttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=SaveAnswerSerializer, responses=AttemptSerializer)
    @action(detail=True, methods=["post"])
    def answers(self, request: Request, pk: str | None = None) -> Response:
        attempt = self.get_object()
        ser = SaveAnswerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.save_answer(
                attempt,
                ser.validated_data["question"],
                ser.validated_data["response"],
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        attempt.refresh_from_db()
        return Response(AttemptSerializer(attempt).data)

    @extend_schema(request=None, responses=AttemptSerializer)
    @action(detail=True, methods=["post"])
    def finish(self, request: Request, pk: str | None = None) -> Response:
        attempt = self.get_object()
        services.finish_attempt(attempt)
        return Response(AttemptSerializer(attempt).data)

    @extend_schema(request=SelfAssessSerializer, responses=AttemptSerializer)
    @action(detail=True, methods=["post"], url_path="self-assess")
    def self_assess(self, request: Request, pk: str | None = None) -> Response:
        attempt = self.get_object()
        ser = SelfAssessSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.self_assess(
                attempt,
                ser.validated_data["question"],
                ser.validated_data["scores"],
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        attempt.refresh_from_db()
        return Response(AttemptSerializer(attempt).data)

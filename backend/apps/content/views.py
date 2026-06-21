from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.serializers import BaseSerializer

from .models import Test
from .serializers import TestDetailSerializer, TestListSerializer


class TestViewSet(viewsets.ReadOnlyModelViewSet[Test]):
    def get_queryset(self) -> QuerySet[Test]:
        qs = Test.objects.filter(is_published=True)
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                "sections__task_groups__questions", "sections__section_type"
            )
        return qs

    def get_serializer_class(self) -> type[BaseSerializer[Test]]:
        return TestDetailSerializer if self.action == "retrieve" else TestListSerializer

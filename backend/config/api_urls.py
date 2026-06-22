from rest_framework.routers import DefaultRouter

from apps.attempts.views import AttemptViewSet
from apps.content.views import TestViewSet

router = DefaultRouter()
router.register("attempts", AttemptViewSet, basename="attempt")
router.register("tests", TestViewSet, basename="test")

urlpatterns = router.urls

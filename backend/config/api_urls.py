from rest_framework.routers import DefaultRouter

from apps.content.views import TestViewSet

router = DefaultRouter()
router.register("tests", TestViewSet, basename="test")

urlpatterns = router.urls

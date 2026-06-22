from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.attempts.views import AttemptViewSet
from apps.content.views import TestViewSet

router = DefaultRouter()
router.register("attempts", AttemptViewSet, basename="attempt")
router.register("tests", TestViewSet, basename="test")

urlpatterns = [
    *router.urls,
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

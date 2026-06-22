from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.users.models import User


class UserModelTests(TestCase):
    def test_create_user(self) -> None:
        user = get_user_model().objects.create_user(
            username="alice", password="pw12345!"
        )
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.is_active)


class JWTAuthTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="u", password="pw12345!")

    def test_obtain_and_use_token(self) -> None:
        r = self.client.post(
            "/api/v1/auth/token/",
            {"username": "u", "password": "pw12345!"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        access = r.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(self.client.get("/api/v1/tests/").status_code, 200)

    def test_no_token_rejected(self) -> None:
        self.assertEqual(self.client.get("/api/v1/tests/").status_code, 401)

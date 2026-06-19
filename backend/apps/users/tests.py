from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_create_user(self) -> None:
        user = get_user_model().objects.create_user(
            username="alice", password="pw12345!"
        )
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.is_active)

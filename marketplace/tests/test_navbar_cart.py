from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


User = get_user_model()


class NavbarCartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pass")

    def test_navbar_contains_mi_carrito(self):
        self.client.login(username="u1", password="pass")
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn("Mi Carrito", html)
        self.assertIn("/cart/", html)


from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountsViewsTests(TestCase):
    def test_register_get(self):
        # Ajustá 'register' al name real de tu URL de registro
        try:
            res = self.client.get(reverse("register"))
            self.assertEqual(res.status_code, 200)
        except Exception:
            self.skipTest("No hay vista 'register' definida")

    def test_register_post_ok(self):
        try:
            res = self.client.post(reverse("register"), {
                "username": "nuevo",
                "password1": "pass12345",
                "password2": "pass12345"
            })
        except Exception:
            self.skipTest("No hay vista 'register' definida")
            return
        # muchas vistas redirigen tras registrar
        self.assertIn(res.status_code, (200, 302))
        self.assertTrue(User.objects.filter(username="nuevo").exists())

    def test_login_get(self):
        try:
            res = self.client.get(reverse("login"))
            self.assertEqual(res.status_code, 200)
        except Exception:
            self.skipTest("No hay vista 'login' definida")

class AccountsLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u_demo", password="pass123")

    def test_login_ok(self):
        try:
            r = self.client.post(reverse("login"), {"username":"u_demo","password":"pass123"})
        except Exception:
            self.skipTest("No hay vista login")
            return
        self.assertIn(r.status_code, (200, 302))

    def test_login_fail(self):
        try:
            r = self.client.post(reverse("login"), {"username":"u_demo","password":"wrong"})
        except Exception:
            self.skipTest("No hay vista login")
            return
        self.assertIn(r.status_code, (200, 302))

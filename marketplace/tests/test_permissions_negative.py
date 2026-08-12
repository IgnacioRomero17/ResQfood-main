from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.core import signing

from marketplace.models import Partner, Pack, Order


User = get_user_model()


class PermissionsNegativeTests(TestCase):
    """Negative-path permission and scoping checks.

    - Orders list requires auth (401/403 depending on auth backend)
    - Cross-user order detail yields 404 (scoped queryset)
    - Redeem by non-owner partner is 403
    - Cancel by non-owner/non-order-user yields 404 or 403 (documented acceptable)
    - verify-qr requires auth (401/403) in our setup
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", password="pass123")
        self.other = User.objects.create_user(username="u2", password="pass123")
        self.owner = User.objects.create_user(username="owner", password="pass123")

        self.partner = Partner.objects.create(
            owner=self.owner,
            categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local",
            direccion="x",
        )
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner,
            titulo="Pack",
            etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000,
            precio_oferta=500,
            stock=1,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=1),
        )

        # user reserves an order
        self.client.login(username="u1", password="pass123")
        reservar_url = reverse("pack-reservar", args=[self.pack.id])
        r = self.client.post(reservar_url)
        self.assertEqual(r.status_code, 201)
        self.order_id = r.json()["order_id"]
        self.client.logout()

    def test_orders_list_requires_auth(self):
        res = self.client.get(reverse("order-list"))
        self.assertIn(res.status_code, (401, 403))

    def test_other_users_order_detail_is_404(self):
        # user u2 tries to access order of u1
        self.client.login(username="u2", password="pass123")
        url = reverse("order-detail", args=[self.order_id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_redeem_by_non_owner_partner_is_403(self):
        # non-owner tries to redeem
        self.client.login(username="u2", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertIn(res.status_code, (403, 400))

    def test_cancel_by_non_owner_is_404_or_403(self):
        # non-order user attempts to cancel
        self.client.login(username="u2", password="pass123")
        url = reverse("order-cancel", args=[self.order_id])
        res = self.client.post(url)
        # Queryset scoping produces 404; 403 also acceptable if view changes
        self.assertIn(res.status_code, (404, 403))

    def test_verify_qr_requires_auth_or_is_limited_if_public(self):
        # currently protected → expect 401/403
        token = signing.dumps({"order_id": self.order_id, "pack_id": self.pack.id})
        url = reverse("order-verify-qr")
        res = self.client.post(url, {"token": token}, format="json")
        self.assertIn(res.status_code, (401, 403))


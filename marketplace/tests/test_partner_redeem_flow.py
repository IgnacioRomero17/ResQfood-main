from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.core import signing

from marketplace.models import Partner, Pack, Order

User = get_user_model()


class PartnerRedeemFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="own", password="pass123")
        self.other = User.objects.create_user(username="oth", password="pass123")
        self.user = User.objects.create_user(username="u1", password="pass123")

        self.partner = Partner.objects.create(
            owner=self.owner,
            categoria=Partner.Categoria.RESTAURANTE,
            nombre="Parrilla Donde",
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

        # Crear una orden pendiente del usuario
        self.client.login(username="u1", password="pass123")
        reservar = self.client.post(reverse("pack-reservar", args=[self.pack.id]))
        self.assertEqual(reservar.status_code, 201)
        self.order_id = reservar.json()["order_id"]
        self.client.logout()

    def test_verify_qr_success_and_invalid(self):
        token = signing.dumps({"order_id": self.order_id, "pack_id": self.pack.id})
        self.client.login(username="own", password="pass123")
        url = reverse("order-verify-qr")

        ok = self.client.post(url, {"token": token}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.json()["order_id"], self.order_id)

        bad = self.client.post(url, {"token": "invalid-token"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_redeem_success_owner(self):
        self.client.login(username="own", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200, res.content)
        o = Order.objects.get(id=self.order_id)
        self.assertEqual(o.estado, Order.Estado.RETIRADO)

    def test_redeem_forbidden_not_owner(self):
        self.client.login(username="oth", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertIn(res.status_code, (403, 400))

    def test_redeem_out_of_window(self):
        # mover inicio para el futuro
        p = Pack.objects.get(id=self.pack.id)
        p.pickup_start = timezone.now() + timedelta(hours=2)
        p.save(update_fields=["pickup_start"])

        self.client.login(username="own", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 400)
        self.assertIn("franja", res.json()["detail"].lower())


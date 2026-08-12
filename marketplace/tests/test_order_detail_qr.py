from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from marketplace.models import Partner, Pack, Order

User = get_user_model()

class OrderDetailAndQRTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", password="pass")
        owner = User.objects.create_user("owner", password="pass")
        partner = Partner.objects.create(
            owner=owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="QR Local", direccion="x"
        )
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=partner, titulo="Pack QR", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=1,
            pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2)
        )
        self.order = Order.objects.create(
            user=self.u1, pack=self.pack, precio_pagado=self.pack.precio_oferta,
            estado=Order.Estado.PENDIENTE
        )

    def test_order_detail_requires_login(self):
        res = self.client.get(reverse("order_detail", args=[self.order.id]))
        # Redirect a login (302) o 302 + Location
        self.assertIn(res.status_code, (302, 301))

    def test_order_detail_ok_and_qr(self):
        self.client.login(username="u1", password="pass")
        r = self.client.get(reverse("order_detail", args=[self.order.id]))
        self.assertEqual(r.status_code, 200)

        # PNG del QR
        qr = self.client.get(reverse("order_qr", args=[self.order.id]))
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(qr["Content-Type"], "image/png")

    def test_order_qr_forbidden_other_user(self):
        other = User.objects.create_user("other", password="pass")
        self.client.login(username="other", password="pass")
        res = self.client.get(reverse("order_qr", args=[self.order.id]))
        self.assertIn(res.status_code, (404, 403))  # según tu implementación

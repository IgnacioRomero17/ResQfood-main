from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from marketplace.models import Partner, Pack, Order

User = get_user_model()


class OrderQRVisibilityTests(TestCase):
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

    def test_qr_hidden_when_not_paid(self):
        # create pending
        order = Order.objects.create(
            user=self.u1, pack=self.pack, precio_pagado=self.pack.precio_oferta,
            estado=Order.Estado.PENDIENTE
        )
        self.client.login(username="u1", password="pass")
        res = self.client.get(reverse("order_detail", args=[order.id]))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        # message shown, img not rendered
        self.assertIn("El QR aparecer", html)
        self.assertNotIn("/qr.png", html)

    def test_qr_shown_when_paid(self):
        order = Order.objects.create(
            user=self.u1, pack=self.pack, precio_pagado=self.pack.precio_oferta,
            estado=Order.Estado.PENDIENTE
        )
        # mark as paid
        order.estado = Order.Estado.PAGADO
        order.save(update_fields=["estado"])

        self.client.login(username="u1", password="pass")
        res = self.client.get(reverse("order_detail", args=[order.id]))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        # img should be present
        self.assertIn("/qr.png", html)


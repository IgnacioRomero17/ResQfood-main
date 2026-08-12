from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from payments.models import Payment
from marketplace.models import Order, Pack, Partner


User = get_user_model()


class ManualApproveTest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="admin", password="x", is_staff=True, is_superuser=True)
        self.user = User.objects.create_user(username="u", password="x")
        owner = User.objects.create_user(username="owner", password="x")
        partner = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre="Comercio", direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=partner, titulo="P1", etiqueta=Pack.Etiqueta.EXCEDENTE,
            stock=5,
            precio_original=1000, precio_oferta=900,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=1),
        )
        self.order = Order.objects.create(user=self.user, pack=self.pack, estado=Order.Estado.PENDIENTE, precio_pagado=900)
        self.pay = Payment.objects.create(order=self.order, provider="efectivo", status="pending")

    def test_staff_mark_approved(self):
        self.client.force_login(self.staff)
        url = reverse("payments_mark_approved", args=[self.pay.id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200, r.content)
        self.pay.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.pay.status, "approved")
        self.assertEqual(self.order.estado, Order.Estado.PAGADO)

    def test_not_staff_forbidden(self):
        self.client.force_login(self.user)
        url = reverse("payments_mark_approved", args=[self.pay.id])
        r = self.client.post(url)
        # staff_member_required redirige al login de admin por defecto
        self.assertIn(r.status_code, (302, 403))


from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order
from payments.models import Payment

User = get_user_model()


class PaymentStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        other = User.objects.create_user('u2', password='pass')
        powner = User.objects.create_user('powner', password='pass')
        partner = Partner.objects.create(owner=powner, categoria=Partner.Categoria.RESTAURANTE, nombre='Loc', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=partner, titulo='T', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=2,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.order = Order(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta, estado=Order.Estado.PENDIENTE)
        self.order._skip_stock = True
        self.order.save()
        self.status_url = reverse('payment_status', args=[self.order.id])

    def test_status_requires_login(self):
        r = self.client.get(self.status_url)
        self.assertIn(r.status_code, (302, 403))

    def test_status_non_owner_403(self):
        self.client.login(username='u2', password='pass')
        r = self.client.get(self.status_url)
        self.assertEqual(r.status_code, 403)

    def test_status_pending_before_approve(self):
        self.client.login(username='u1', password='pass')
        # create a created payment
        Payment.objects.create(order=self.order, provider='mp', preference_id='PREF', status='created')
        r = self.client.get(self.status_url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['order_estado'], Order.Estado.PENDIENTE)
        self.assertIsNone(data['paid_at'])
        self.assertIn('payment', data)

    def test_status_after_mock_approve(self):
        self.client.login(username='u1', password='pass')
        Payment.objects.create(order=self.order, provider='mp', preference_id='PREF', status='created')
        # simulate webhook/approval via mark_paid
        self.order.mark_paid()
        r = self.client.get(self.status_url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['order_estado'], Order.Estado.PAGADO)
        self.assertIsNotNone(data['paid_at'])
        self.assertIn('payment', data)


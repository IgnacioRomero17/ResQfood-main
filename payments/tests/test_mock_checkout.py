from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order

User = get_user_model()


class MockCheckoutTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('u1', password='pass')
        self.other = User.objects.create_user('u2', password='pass')
        powner = User.objects.create_user('powner', password='pass')
        self.partner = Partner.objects.create(owner=powner, categoria=Partner.Categoria.RESTAURANTE, nombre='Loc', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='T', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=2,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        # create as checkout-style (no stock decrement yet)
        self.order = Order(user=self.owner, pack=self.pack, precio_pagado=self.pack.precio_oferta, estado=Order.Estado.PENDIENTE)
        self.order._skip_stock = True
        self.order.save()

    @override_settings(PAYMENTS_USE_LOCAL_MOCK=False)
    def test_mock_disabled_returns_404(self):
        self.client.login(username='u1', password='pass')
        r1 = self.client.get(reverse('mp_mock', args=[self.order.id]))
        self.assertEqual(r1.status_code, 404)
        r2 = self.client.post(reverse('mp_mock_approve', args=[self.order.id]))
        self.assertEqual(r2.status_code, 404)

    @override_settings(PAYMENTS_USE_LOCAL_MOCK=True)
    def test_non_owner_gets_403(self):
        self.client.login(username='u2', password='pass')
        r1 = self.client.get(reverse('mp_mock', args=[self.order.id]))
        self.assertEqual(r1.status_code, 403)
        r2 = self.client.post(reverse('mp_mock_approve', args=[self.order.id]))
        self.assertEqual(r2.status_code, 403)

    @override_settings(PAYMENTS_USE_LOCAL_MOCK=True)
    def test_double_approve_no_double_stock(self):
        self.client.login(username='u1', password='pass')
        before = Pack.objects.get(id=self.pack.id).stock
        r1 = self.client.post(reverse('mp_mock_approve', args=[self.order.id]))
        self.assertIn(r1.status_code, (302, 303))
        mid = Pack.objects.get(id=self.pack.id).stock
        self.assertEqual(mid, before - 1)
        # second approval does not decrement again
        r2 = self.client.post(reverse('mp_mock_approve', args=[self.order.id]))
        self.assertIn(r2.status_code, (302, 303))
        after = Pack.objects.get(id=self.pack.id).stock
        self.assertEqual(after, mid)


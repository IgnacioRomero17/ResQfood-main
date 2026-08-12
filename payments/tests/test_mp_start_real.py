from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order
from payments.models import Payment

User = get_user_model()


class MPStartRealTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        powner = User.objects.create_user('powner', password='pass')
        self.partner = Partner.objects.create(owner=powner, categoria=Partner.Categoria.RESTAURANTE, nombre='Loc', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='T', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=2,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.order = Order(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta, estado=Order.Estado.PENDIENTE)
        self.order._skip_stock = True
        self.order.save()
        self.url = reverse('mp_start', args=[self.order.id])

    @override_settings(PAYMENTS_USE_LOCAL_MOCK=True)
    def test_start_uses_mock_when_flag_true(self):
        self.client.login(username='u1', password='pass')
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('/api/payments/mp/mock/', data['init_point'])

    @override_settings(PAYMENTS_USE_LOCAL_MOCK=False)
    @patch('payments.gateways.mercadopago.mercadopago')
    def test_start_creates_preference_when_flag_false(self, mock_mp):
        class Pref:
            def create(self, body):
                return {"response": {"id": "PREF-123", "init_point": "https://www.mercadopago.com/init", "sandbox_init_point": "https://sandbox.mercadopago.com/init"}}
        class SDK:
            def __init__(self, token): pass
            def preference(self): return Pref()
        mock_mp.SDK = SDK
        self.client.login(username='u1', password='pass')
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data['preference_id'], 'PREF-123')
        self.assertIn('mercadopago.com', data['init_point'])
        self.assertTrue(Payment.objects.filter(order=self.order, provider='mp', preference_id='PREF-123', status='pending').exists())

    @override_settings(PAYMENTS_USE_LOCAL_MOCK=False)
    @patch('payments.gateways.mercadopago.mercadopago')
    def test_start_handles_sdk_error(self, mock_mp):
        class SDK:
            def __init__(self, token): pass
            def preference(self):
                class P:
                    def create(self, body):
                        raise RuntimeError('boom')
                return P()
        mock_mp.SDK = SDK
        self.client.login(username='u1', password='pass')
        r = self.client.post(self.url)
        self.assertIn(r.status_code, (500, 503))
        self.assertEqual(Payment.objects.count(), 0)


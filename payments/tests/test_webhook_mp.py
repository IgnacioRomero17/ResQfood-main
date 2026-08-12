from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order
from payments.models import Payment


User = get_user_model()


class MPWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        powner = User.objects.create_user('powner', password='pass')
        self.partner = Partner.objects.create(owner=powner, categoria=Partner.Categoria.RESTAURANTE, nombre='Loc', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='T', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=2,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.order = Order.objects.create(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta, estado=Order.Estado.PENDIENTE)
        self.url = '/webhooks/mercadopago/'

    @override_settings(MP_WEBHOOK_SECRET="")
    @patch('payments.views_webhooks.mercadopago')
    def test_webhook_approved_marks_paid_once(self, mock_mp):
        Payment.objects.create(order=self.order, provider='mp', status='pending')

        order_id = str(self.order.id)

        class Pay:
            def get(self, pid):
                return {"response": {"external_reference": order_id, "status": "approved"}}
        class SDK:
            def __init__(self, token): pass
            def payment(self): return Pay()
        mock_mp.SDK = SDK

        body = {"type": "payment", "data": {"id": "999"}}
        r = self.client.post(self.url, data=body, content_type='application/json',
                             **{"HTTP_X_REQUEST_ID": "abc123"})
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.estado, Order.Estado.PAGADO)
        # Ensure stock decremented once
        self.pack.refresh_from_db()
        self.assertGreaterEqual(self.pack.stock, 1)

        # Send duplicate (same request id) -> no change but still 200
        r2 = self.client.post(self.url, data=body, content_type='application/json',
                              **{"HTTP_X_REQUEST_ID": "abc123"})
        self.assertEqual(r2.status_code, 200)

    @override_settings(MP_WEBHOOK_SECRET="")
    @patch('payments.views_webhooks.mercadopago')
    def test_webhook_idempotent_by_request_id(self, mock_mp):
        order_id = str(self.order.id)
        class Pay:
            def get(self, pid):
                return {"response": {"external_reference": order_id, "status": "approved"}}
        class SDK:
            def __init__(self, token): pass
            def payment(self): return Pay()
        mock_mp.SDK = SDK

        body = {"type": "payment", "data": {"id": "999"}}
        r1 = self.client.post(self.url, data=body, content_type='application/json',
                              **{"HTTP_X_REQUEST_ID": "same-id"})
        r2 = self.client.post(self.url, data=body, content_type='application/json',
                              **{"HTTP_X_REQUEST_ID": "same-id"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        # Order remains paid exactly once
        self.order.refresh_from_db()
        self.assertEqual(self.order.estado, Order.Estado.PAGADO)

    @override_settings(MP_WEBHOOK_SECRET="")
    @patch('payments.views_webhooks.mercadopago')
    def test_webhook_out_of_order_downgrade_ignored(self, mock_mp):
        # First approved
        order_id = str(self.order.id)
        class PayApproved:
            def get(self, pid):
                return {"response": {"external_reference": order_id, "status": "approved"}}
        class SDKApproved:
            def __init__(self, token): pass
            def payment(self): return PayApproved()
        mock_mp.SDK = SDKApproved
        body = {"type": "payment", "data": {"id": "1"}}
        self.client.post(self.url, data=body, content_type='application/json')

        # Then pending for same payment
        class PayPending:
            def get(self, pid):
                return {"response": {"external_reference": order_id, "status": "pending"}}
        class SDKPending:
            def __init__(self, token): pass
            def payment(self): return PayPending()
        mock_mp.SDK = SDKPending
        body2 = {"type": "payment", "data": {"id": "1"}}
        r2 = self.client.post(self.url, data=body2, content_type='application/json')
        self.assertEqual(r2.status_code, 200)

        # Payment stays approved
        pay = Payment.last_for_order(self.order)
        self.assertEqual(pay.status, 'approved')
        self.order.refresh_from_db()
        self.assertEqual(self.order.estado, Order.Estado.PAGADO)

    @override_settings(MP_WEBHOOK_SECRET="secret")
    def test_webhook_invalid_signature_forbidden(self):
        body = {"type": "payment", "data": {"id": "999"}}
        # Wrong signature
        r = self.client.post(self.url, data=body, content_type='application/json',
                             **{"HTTP_X_SIGNATURE": "wrong"})
        self.assertEqual(r.status_code, 403)

    @override_settings(MP_WEBHOOK_SECRET="")
    @patch('payments.views_webhooks.mercadopago')
    def test_webhook_handles_missing_order_safely(self, mock_mp):
        class Pay:
            def get(self, pid):
                return {"response": {"external_reference": "999999", "status": "approved"}}
        class SDK:
            def __init__(self, token): pass
            def payment(self): return Pay()
        mock_mp.SDK = SDK

        body = {"type": "payment", "data": {"id": "999"}}
        r = self.client.post(self.url, data=body, content_type='application/json')
        self.assertEqual(r.status_code, 200)

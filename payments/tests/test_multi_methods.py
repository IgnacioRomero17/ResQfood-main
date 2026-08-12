from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order
from payments.models import Payment


User = get_user_model()


class MultiMethodsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        powner = User.objects.create_user('powner', password='pass')
        self.partner = Partner.objects.create(owner=powner, categoria=Partner.Categoria.RESTAURANTE, nombre='Loc', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='T', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=2,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.order = Order.objects.create(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta,
                                          estado=Order.Estado.PENDIENTE, metodo_pago='mp')

    def login(self):
        self.client.login(username='u1', password='pass')

    def test_select_method_owner_ok(self):
        self.login()
        url = reverse('payments_select_method', args=[self.order.id])
        r = self.client.post(url, {'metodo_pago': 'efectivo'})
        self.assertEqual(r.status_code, 200, r.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.metodo_pago, 'efectivo')

    def test_select_method_forbidden_other_user(self):
        other = User.objects.create_user('u2', password='pass')
        self.client.login(username='u2', password='pass')
        url = reverse('payments_select_method', args=[self.order.id])
        r = self.client.post(url, {'metodo_pago': 'transferencia'})
        self.assertEqual(r.status_code, 403)

    def test_select_method_invalid_or_state(self):
        self.login()
        # invalid method
        url = reverse('payments_select_method', args=[self.order.id])
        r = self.client.post(url, {'metodo_pago': 'x'})
        self.assertEqual(r.status_code, 400)
        # change state and try again
        self.order.estado = Order.Estado.PAGADO
        self.order.save(update_fields=['estado'])
        r2 = self.client.post(url, {'metodo_pago': 'mp'})
        self.assertEqual(r2.status_code, 400)

    def test_cash_start_flow_and_idempotent(self):
        self.login()
        self.order.metodo_pago = 'efectivo'
        self.order.save(update_fields=['metodo_pago'])
        url = reverse('payments_cash_start', args=[self.order.id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(Payment.objects.filter(order=self.order, provider='efectivo', status='pending').exists())
        # idempotent
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(Payment.objects.filter(order=self.order, provider='efectivo').count(), 1)

    def test_transfer_start_flow_and_idempotent(self):
        self.login()
        self.order.metodo_pago = 'transferencia'
        self.order.save(update_fields=['metodo_pago'])
        url = reverse('payments_transfer_start', args=[self.order.id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(Payment.objects.filter(order=self.order, provider='transferencia', status='pending').exists())
        # idempotent
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(Payment.objects.filter(order=self.order, provider='transferencia').count(), 1)

    def test_cash_transfer_wrong_state_or_method(self):
        self.login()
        # wrong method for cash
        url_cash = reverse('payments_cash_start', args=[self.order.id])
        r = self.client.post(url_cash)
        self.assertEqual(r.status_code, 400)
        # wrong method for transfer
        url_tr = reverse('payments_transfer_start', args=[self.order.id])
        r2 = self.client.post(url_tr)
        self.assertEqual(r2.status_code, 400)

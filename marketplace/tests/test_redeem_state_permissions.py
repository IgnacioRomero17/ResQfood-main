from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order

User = get_user_model()


class RedeemStatePermissionsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass')
        self.other = User.objects.create_user('other', password='pass')
        self.u1 = User.objects.create_user('u1', password='pass')
        self.partner = Partner.objects.create(owner=self.owner, categoria=Partner.Categoria.RESTAURANTE, nombre='X', direccion='y')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='T', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=1,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=1))

    def _make_order(self, estado=Order.Estado.PENDIENTE):
        return Order.objects.create(user=self.u1, pack=self.pack, precio_pagado=self.pack.precio_oferta, estado=estado)

    def test_non_owner_gets_403_even_if_redeemed(self):
        o = self._make_order(estado=Order.Estado.RETIRADO)
        self.client.login(username='other', password='pass')
        res = self.client.post(reverse('order-redeem', args=[o.id]))
        self.assertEqual(res.status_code, 403)

    def test_owner_paid_redeem_ok(self):
        o = self._make_order(estado=Order.Estado.PAGADO)
        self.client.login(username='owner', password='pass')
        res = self.client.post(reverse('order-redeem', args=[o.id]))
        self.assertEqual(res.status_code, 200)
        o.refresh_from_db()
        self.assertEqual(o.estado, Order.Estado.RETIRADO)


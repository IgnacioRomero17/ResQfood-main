from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order

User = get_user_model()


class CheckoutRedirectBacklinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        owner = User.objects.create_user('owner', password='pass')
        self.partner = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='P', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=2,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))

    def test_after_checkout_detail_links_back_to_cart(self):
        self.client.login(username='u1', password='pass')
        # add to cart
        self.client.post(reverse('cart-add'), {"pack_id": self.pack.id}, format='json')
        # checkout
        r = self.client.post(reverse('cart-checkout'))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        url = data.get('detail_url') or data.get('redirect')
        self.assertIn('/orders/', url)
        self.assertIn('from=cart', url)
        detail = self.client.get(url)
        html = detail.content.decode()
        self.assertIn('href="/cart/"', html)
        self.assertIn('Detalle del pedido', html)
        self.assertIn('Pagar ahora', html)

    def test_direct_detail_links_back_to_mis_reservas(self):
        self.client.login(username='u1', password='pass')
        # place a single order directly (bypass cart)
        o = Order.objects.create(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta)
        r = self.client.get(reverse('order_detail', args=[o.id]))
        html = r.content.decode()
        self.assertIn('href="/mis-reservas/"', html)

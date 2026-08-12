from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order


User = get_user_model()


class MisReservasUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pass")
        owner = User.objects.create_user("owner", password="pass")
        self.partner = Partner.objects.create(
            owner=owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local Tabs", direccion="x"
        )
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner, titulo="Pack UI", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=5,
            pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2)
        )
        # create two orders with different estados
        self.o1 = Order.objects.create(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta,
                                       estado=Order.Estado.PENDIENTE)
        self.o2 = Order.objects.create(user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta,
                                       estado=Order.Estado.PAGADO)

    def test_tabs_and_data_attributes_present(self):
        self.client.login(username="u1", password="pass")
        res = self.client.get(reverse("mis_reservas"))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()

        # tabs markup
        self.assertIn('role="tablist"', html)
        self.assertIn('role="tab"', html)
        self.assertIn('data-filter="pendiente"', html)
        self.assertIn('data-filter="pagado"', html)
        self.assertIn('data-filter="retirado"', html)
        self.assertIn('data-filter="expirado"', html)
        self.assertIn('data-filter="cancelado"', html)

        # card data attributes: estado and pickup-end in ISO
        self.assertIn(f'data-estado="{self.o1.estado}"', html)
        self.assertIn(f'data-estado="{self.o2.estado}"', html)
        self.assertIn('data-pickup-end="', html)

        # JS snippet visible
        self.assertIn('setInterval(updateCountdown', html)


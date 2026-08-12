from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Order, Pack, Partner


User = get_user_model()


class MyOrdersTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("u", password="x")
        self.client.force_login(self.u)
        owner = User.objects.create_user("owner", password="x")
        partner = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre="Comercio A", direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=partner, titulo="Pack 1", etiqueta=Pack.Etiqueta.EXCEDENTE,
            stock=5,
            precio_original=1000, precio_oferta=900,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=1),
        )

    def test_lista_basica(self):
        o = Order.objects.create(user=self.u, pack=self.pack, estado=Order.Estado.PENDIENTE, precio_pagado=900, metodo_pago="mp")
        r = self.client.get(reverse("my_orders"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f"#{o.id}")

    def test_filtro_estado(self):
        Order.objects.create(user=self.u, pack=self.pack, estado=Order.Estado.PAGADO, precio_pagado=900, metodo_pago="mp")
        r = self.client.get(reverse("my_orders")+"?estado=pagado")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Pagado")

    def test_paginacion(self):
        for i in range(30):
            o = Order(user=self.u, pack=self.pack, estado=Order.Estado.PENDIENTE, precio_pagado=900, metodo_pago="mp")
            o._skip_stock = True
            o.save()
        r = self.client.get(reverse("my_orders"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Mis pedidos")

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order

User = get_user_model()

class ExpirarOrdenesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass123")
        owner = User.objects.create_user(username="owner", password="pass123")
        partner = Partner.objects.create(
            owner=owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local", direccion="x"
        )

        now = timezone.now()
        # 1) crear pack con ventana VÁLIDA para poder crear la orden
        self.pack_expirada = Pack.objects.create(
            partner=partner, titulo="Vieja", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=5,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=1),   # válida ahora
        )
        self.pack_vigente = Pack.objects.create(
            partner=partner, titulo="Nueva", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=5,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=3),
        )

        # 2) crear órdenes (creación válida)
        self.order_expirada = Order.objects.create(
            user=self.user, pack=self.pack_expirada,
            precio_pagado=self.pack_expirada.precio_oferta,
            estado=Order.Estado.PENDIENTE
        )
        self.order_vigente = Order.objects.create(
            user=self.user, pack=self.pack_vigente,
            precio_pagado=self.pack_vigente.precio_oferta,
            estado=Order.Estado.PENDIENTE
        )

        # 3) ahora sí: volver expirada la ventana del primer pack
        self.pack_expirada.pickup_end = now - timedelta(minutes=1)
        self.pack_expirada.save(update_fields=["pickup_end"])

    def test_expire_orders_command(self):
        call_command("expire_orders", "--dry-run")
        self.order_expirada.refresh_from_db()
        self.assertEqual(self.order_expirada.estado, Order.Estado.PENDIENTE)

        call_command("expire_orders")
        self.order_expirada.refresh_from_db()
        self.order_vigente.refresh_from_db()
        self.assertEqual(self.order_expirada.estado, Order.Estado.EXPIRADO)
        self.assertEqual(self.order_vigente.estado, Order.Estado.PENDIENTE)

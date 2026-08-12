from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from marketplace.models import Partner, Pack, Order
from marketplace.serializers import PackSerializer, OrderLiteSerializer

User = get_user_model()

class SerializerCoverageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pass")
        owner = User.objects.create_user("owner", password="pass")
        self.partner = Partner.objects.create(
            owner=owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local", direccion="Calle X"
        )
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner, titulo="Pack Serializer", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=3,
            pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2)
        )
        self.order = Order.objects.create(
            user=self.user, pack=self.pack, precio_pagado=self.pack.precio_oferta,
            estado=Order.Estado.PENDIENTE
        )

    def test_pack_serializer_read(self):
        data = PackSerializer(self.pack).data
        # Campos básicos expuestos
        self.assertEqual(data["titulo"], "Pack Serializer")
        self.assertEqual(int(data["stock"]), 3)
        self.assertEqual(data["partner"], self.partner.id)

    def test_order_lite_serializer_read(self):
        data = OrderLiteSerializer(self.order).data
        # Campos "enriquecidos"
        self.assertEqual(data["pack"], self.pack.id)
        self.assertEqual(data["pack_titulo"], "Pack Serializer")
        self.assertEqual(data["partner_nombre"], "Local")
        self.assertIn("pickup_start", data)
        self.assertIn("pickup_end", data)
        # imagen puede ser null/None y está bien

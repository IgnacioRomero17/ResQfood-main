from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta

from marketplace.models import Partner, Pack, Order

User = get_user_model()

class ReservaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", password="pass123")
        self.partner_owner = User.objects.create_user(username="owner", password="pass123")

        self.partner = Partner.objects.create(
            owner=self.partner_owner,
            categoria=Partner.Categoria.RESTAURANTE,
            nombre="Mi Local",
            direccion="Calle 123",
        )

        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner,
            titulo="Pack Prueba",
            etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000,
            precio_oferta=500,
            stock=2,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=3),
        )

        self.client.login(username="u1", password="pass123")

    def test_reservar_ok_descuenta_stock(self):
        url = reverse("pack-reservar", args=[self.pack.id])  # DefaultRouter genera <basename>-reservar
        res = self.client.post(url)
        self.assertEqual(res.status_code, 201, res.content)
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.stock, 1)
        self.assertTrue(Order.objects.filter(user=self.user, pack=self.pack).exists())

    def test_reservar_sin_stock_conflict(self):
        self.pack.stock = 0
        self.pack.save(update_fields=["stock"])
        url = reverse("pack-reservar", args=[self.pack.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 409)
        self.assertIn("Sin stock", res.json()["detail"])

    def test_reservar_fuera_de_ventana_expirada(self):
        self.pack.pickup_end = timezone.now() - timedelta(minutes=1)
        self.pack.save(update_fields=["pickup_end"])
        url = reverse("pack-reservar", args=[self.pack.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 409)
        self.assertIn("expiró", res.json()["detail"])

    def test_reservar_no_duplicar_para_mismo_usuario(self):
        url = reverse("pack-reservar", args=[self.pack.id])
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 201)

        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 409)
        self.assertIn("Ya reservaste", r2.json()["detail"])

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from marketplace.models import Pack, Partner


class FiltersTest(TestCase):
    def setUp(self):
        User = get_user_model()
        owner = User.objects.create_user("owner", password="pass")
        m = Partner.objects.create(nombre="Restó Buen Sabor", categoria=Partner.Categoria.RESTAURANTE, direccion='x', owner=owner)
        now = timezone.now()
        # Pack en oferta y con stock abierto
        Pack.objects.create(
            partner=m, titulo="Promo 1", etiqueta=Pack.Etiqueta.EXCEDENTE,
            stock=5,
            precio_original=1000, precio_oferta=800,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=2),
        )
        # Pack sin oferta, sin stock y fuera de ventana ahora
        Pack.objects.create(
            partner=m, titulo="Sin oferta", etiqueta=Pack.Etiqueta.EXCEDENTE,
            stock=0,
            precio_original=1200, precio_oferta=1200,
            pickup_start=now + timedelta(hours=1),
            pickup_end=now + timedelta(hours=2),
        )

    def test_oferta_filter(self):
        url = reverse("home") + "?oferta=1"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Promo 1")
        self.assertNotContains(r, "Sin oferta")

    def test_stock_filter(self):
        url = reverse("home") + "?stock=1"
        r = self.client.get(url)
        self.assertContains(r, "Promo 1")
        self.assertNotContains(r, "Sin oferta")

    def test_abierto_filter(self):
        url = reverse("home") + "?abierto=1"
        r = self.client.get(url)
        self.assertContains(r, "Promo 1")

    def test_categoria_filter(self):
        url = reverse("home") + "?categoria=restaurantes"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

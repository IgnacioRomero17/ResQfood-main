from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from marketplace.models import Partner, Pack


class ImageHelperTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u", password="x")
        self.partner = Partner.objects.create(
            owner=self.user,
            nombre="Café X", slug="cafe-x", categoria="cafes", direccion="x"
        )

        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner,
            titulo="Desayuno",
            etiqueta="excedente",
            precio_original=1000,
            precio_oferta=900,
            stock=1,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=2),
        )

    def test_partner_stock_url(self):
        url = self.partner.image_or_stock_url
        self.assertTrue(isinstance(url, str) and len(url) > 0)
        self.assertTrue(url.endswith((".jpg", ".jpeg", ".png", ".webp")))

    def test_pack_stock_url(self):
        url = self.pack.image_or_stock_url
        self.assertTrue(isinstance(url, str) and len(url) > 0)
        self.assertTrue(url.endswith((".jpg", ".jpeg", ".png", ".webp")))

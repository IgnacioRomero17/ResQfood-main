from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack


User = get_user_model()


class PartnerDetailTest(TestCase):
    def setUp(self):
        owner = User.objects.create_user("owner", password="x")
        self.partner = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre="Comercio Z", slug="comercio-z", direccion="Calle Falsa 123")
        now = timezone.now()
        Pack.objects.create(
            partner=self.partner, titulo="Pack 1", etiqueta=Pack.Etiqueta.EXCEDENTE,
            stock=5,
            precio_original=1000, precio_oferta=900,
            pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=1),
        )

    def test_por_slug(self):
        r = self.client.get(reverse("partner_detail", args=[self.partner.slug]))
        self.assertContains(r, "Comercio Z")
        self.assertContains(r, "Pack 1")

    def test_por_id(self):
        r = self.client.get(reverse("partner_detail", args=[self.partner.id]))
        self.assertContains(r, "Comercio Z")

    def test_filtro_oferta(self):
        r = self.client.get(reverse("partner_detail", args=[self.partner.slug]) + "?oferta=1")
        self.assertContains(r, "Pack 1")

    def test_orden_precio_desc(self):
        r = self.client.get(reverse("partner_detail", args=[self.partner.slug]) + "?orden=precio-desc")
        self.assertEqual(r.status_code, 200)


from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack

User = get_user_model()


class HomeMerchantsTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('owner', password='pass')
        now = timezone.now()
        self.m1 = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A', short_description='Desc A')
        self.m2 = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre='B')
        Pack.objects.create(partner=self.m1, titulo='P1', etiqueta=Pack.Etiqueta.EXCEDENTE,
                            precio_original=1000, precio_oferta=800, stock=1,
                            pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        # expired pack for m2
        Pack.objects.create(partner=self.m2, titulo='PX', etiqueta=Pack.Etiqueta.EXCEDENTE,
                            precio_original=1000, precio_oferta=800, stock=0,
                            pickup_start=now - timedelta(days=2), pickup_end=now - timedelta(days=1))

    def test_home_shows_only_merchants_with_active_packs(self):
        res = self.client.get(reverse('home'))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn('/merchant/', html)
        self.assertIn(self.m1.nombre, html)
        # ensure second merchant link is not present
        if not self.m2.slug:
            self.m2.slug = 'b'
            self.m2.save(update_fields=['slug'])
        self.assertNotIn(f"/merchant/{self.m2.slug}/", html)
        self.assertIn('packs activos', html)

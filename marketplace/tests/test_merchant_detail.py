from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack

User = get_user_model()


class MerchantDetailTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('owner', password='pass')
        self.user = User.objects.create_user('u1', password='pass')
        now = timezone.now()
        self.m = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A')
        self.p_ok = Pack.objects.create(partner=self.m, titulo='OK', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=800, stock=1,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.p_exp = Pack.objects.create(partner=self.m, titulo='EXP', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                         precio_original=1000, precio_oferta=800, stock=0,
                                         pickup_start=now - timedelta(days=2), pickup_end=now - timedelta(days=1))

    def test_detail_lists_only_vigentes_and_has_add(self):
        # ensure slug exists
        if not self.m.slug:
            self.m.slug = 'a'
            self.m.save(update_fields=['slug'])
        res = self.client.get(reverse('merchant_detail', args=[self.m.slug]))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn('Agregar al carrito', html)
        self.assertIn('OK', html)
        self.assertNotIn('EXP', html)


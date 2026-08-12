from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack


User = get_user_model()


class CartPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        owner = User.objects.create_user('owner', password='pass')
        self.partner = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='A1', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=5,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))

    def test_cart_page_renders(self):
        self.client.login(username='u1', password='pass')
        res = self.client.get(reverse('cart'))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn('Mi Carrito', html)
        self.assertIn('Proceder al pago', html)


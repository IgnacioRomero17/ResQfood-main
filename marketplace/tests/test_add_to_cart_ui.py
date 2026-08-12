from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from marketplace.models import Partner, Pack


User = get_user_model()


class AddToCartUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', password='pass')
        owner = User.objects.create_user('owner', password='pass')
        self.partner = Partner.objects.create(owner=owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A', direccion='x')
        now = timezone.now()
        self.pack = Pack.objects.create(partner=self.partner, titulo='Demo', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                        precio_original=1000, precio_oferta=500, stock=5,
                                        pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))

    def test_listing_has_agregar_button_label(self):
        res = self.client.get(reverse('packs:list'))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        # label appears in JS-rendered template
        self.assertIn('Agregar al carrito', html)

    def test_add_updates_badge_on_home_after_api(self):
        self.client.login(username='u1', password='pass')
        # add via API
        url = reverse('cart-add')
        res = self.client.post(url, {'pack_id': self.pack.id}, format='json')
        self.assertEqual(res.status_code, 200)
        # home should render badge with count 1
        home = self.client.get(reverse('home'))
        self.assertEqual(home.status_code, 200)
        self.assertIn('Mi Carrito', home.content.decode())
        self.assertIn('>1<', home.content.decode())

    def test_unauthenticated_add_redirect_or_denied(self):
        res = self.client.post(reverse('cart-add'), {'pack_id': self.pack.id})
        self.assertIn(res.status_code, (401, 403))


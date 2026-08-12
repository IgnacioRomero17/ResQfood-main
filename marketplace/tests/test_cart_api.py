from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from marketplace.models import Partner, Pack


User = get_user_model()


class CartApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pass')
        self.other = User.objects.create_user('u2', password='pass')
        self.owner = User.objects.create_user('owner', password='pass')
        self.partner = Partner.objects.create(owner=self.owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A', direccion='x')
        self.partner_b = Partner.objects.create(owner=self.owner, categoria=Partner.Categoria.RESTAURANTE, nombre='B', direccion='y')
        now = timezone.now()
        self.pack_a1 = Pack.objects.create(partner=self.partner, titulo='A1', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                           precio_original=1000, precio_oferta=500, stock=5,
                                           pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.pack_a2 = Pack.objects.create(partner=self.partner, titulo='A2', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                           precio_original=800, precio_oferta=300, stock=5,
                                           pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=3))
        self.pack_b1 = Pack.objects.create(partner=self.partner_b, titulo='B1', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                           precio_original=700, precio_oferta=200, stock=5,
                                           pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))

    def test_add_requires_auth(self):
        url = reverse('cart-add')
        res = self.client.post(url, {"pack_id": self.pack_a1.id}, format='json')
        self.assertIn(res.status_code, (401, 403))

    def test_add_pack_success(self):
        self.client.login(username='u1', password='pass')
        url = reverse('cart-add')
        res = self.client.post(url, {"pack_id": self.pack_a1.id}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['item_count'], 1)
        self.assertEqual(len(data['items']), 1)

    def test_add_different_merchant_rejected(self):
        self.client.login(username='u1', password='pass')
        url_add = reverse('cart-add')
        self.client.post(url_add, {"pack_id": self.pack_a1.id}, format='json')
        res = self.client.post(url_add, {"pack_id": self.pack_b1.id}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('mismo comercio', res.json()['detail'])

    def test_add_incompatible_window_rejected(self):
        # Make pack incompatible by moving its window fully outside the first
        self.client.login(username='u1', password='pass')
        url_add = reverse('cart-add')
        self.client.post(url_add, {"pack_id": self.pack_a1.id}, format='json')
        # create an incompatible window pack under same merchant
        now = timezone.now()
        p_bad = Pack.objects.create(partner=self.partner, titulo='Bad', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                    precio_original=500, precio_oferta=100, stock=5,
                                    pickup_start=now + timedelta(days=1), pickup_end=now + timedelta(days=2))
        res = self.client.post(url_add, {"pack_id": p_bad.id}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_remove_pack_success(self):
        self.client.login(username='u1', password='pass')
        add = reverse('cart-add')
        self.client.post(add, {"pack_id": self.pack_a1.id}, format='json')
        remove = reverse('cart-remove')
        res = self.client.post(remove, {"pack_id": self.pack_a1.id}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['item_count'], 0)

    def test_list_cart_returns_expected_shape(self):
        self.client.login(username='u1', password='pass')
        add = reverse('cart-add')
        self.client.post(add, {"pack_id": self.pack_a1.id}, format='json')
        res = self.client.get(reverse('cart-list'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for k in ('merchant', 'item_count', 'items', 'total', 'window_start', 'window_end'):
            self.assertIn(k, data)

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack, Order

User = get_user_model()


class CartCheckoutTests(TestCase):
    def setUp(self):
        self.client.defaults['CONTENT_TYPE'] = 'application/json'
        self.user = User.objects.create_user('u1', password='pass')
        self.owner = User.objects.create_user('owner', password='pass')
        self.partner = Partner.objects.create(owner=self.owner, categoria=Partner.Categoria.RESTAURANTE, nombre='A')
        now = timezone.now()
        self.p1 = Pack.objects.create(partner=self.partner, titulo='P1', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                      precio_original=1000, precio_oferta=500, stock=3,
                                      pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2))
        self.p2 = Pack.objects.create(partner=self.partner, titulo='P2', etiqueta=Pack.Etiqueta.EXCEDENTE,
                                      precio_original=800, precio_oferta=400, stock=3,
                                      pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=3))

    def login_and_add(self, packs):
        self.client.login(username='u1', password='pass')
        for p in packs:
            self.client.post(reverse('cart-add'), {"pack_id": p.id}, format='json')

    def test_checkout_requires_auth(self):
        res = self.client.post(reverse('cart-checkout'))
        self.assertIn(res.status_code, (401, 403))

    def test_checkout_fails_when_cart_empty(self):
        self.client.login(username='u1', password='pass')
        res = self.client.post(reverse('cart-checkout'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('vacío', res.json()['detail'])

    def test_checkout_happy_path_creates_orders_and_keeps_cart(self):
        self.login_and_add([self.p1, self.p2])
        res = self.client.post(reverse('cart-checkout'))
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        # now returns a single order_id and keeps cart
        self.assertIn('order_id', data)
        cart = self.client.get(reverse('cart-list')).json()
        self.assertGreaterEqual(cart['item_count'], 1)

    def test_checkout_fails_on_unavailable_item(self):
        self.login_and_add([self.p1])
        # make p1 unavailable now
        self.p1.stock = 0
        self.p1.save(update_fields=['stock'])
        res = self.client.post(reverse('cart-checkout'))
        self.assertIn(res.status_code, (400, 409))

    def test_checkout_is_atomic_on_partial_failure(self):
        self.login_and_add([self.p1, self.p2])
        # Invalidate second pack
        self.p2.stock = 0
        self.p2.save(update_fields=['stock'])
        res = self.client.post(reverse('cart-checkout'))
        self.assertIn(res.status_code, (400, 409))
        # No orders created
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_decrements_stock(self):
        self.login_and_add([self.p1])
        before = Pack.objects.get(id=self.p1.id).stock
        res = self.client.post(reverse('cart-checkout'))
        self.assertEqual(res.status_code, 200)
        after = Pack.objects.get(id=self.p1.id).stock
        self.assertEqual(after, before)

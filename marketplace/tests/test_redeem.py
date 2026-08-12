from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta

from marketplace.models import Partner, Pack, Order

User = get_user_model()

class RedeemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", password="pass123")
        self.partner_owner = User.objects.create_user(username="owner", password="pass123")
        self.other = User.objects.create_user(username="other", password="pass123")

        self.partner = Partner.objects.create(
            owner=self.partner_owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local", direccion="x"
        )

        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner, titulo="Pack", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=1,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=1),
        )

        # user reserva
        self.client.login(username="u1", password="pass123")
        reservar_url = reverse("pack-reservar", args=[self.pack.id])
        r = self.client.post(reservar_url)
        self.assertEqual(r.status_code, 201)
        self.order_id = r.json()["order_id"]
        self.client.logout()

    def test_redeem_ok_por_owner(self):
        # El dueño del partner marca como retirado
        self.client.login(username="owner", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200, res.content)
        o = Order.objects.get(id=self.order_id)
        self.assertEqual(o.estado, Order.Estado.RETIRADO)

    def test_redeem_forbidden_si_no_owner(self):
        self.client.login(username="other", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertIn(res.status_code, (403, 400))

    def test_redeem_fuera_de_franja(self):
        # Mover ventana fuera de rango
        p = Pack.objects.get(id=self.pack.id)
        p.pickup_start = timezone.now() + timedelta(hours=1)
        p.save(update_fields=["pickup_start"])

        self.client.login(username="owner", password="pass123")
        url = reverse("order-redeem", args=[self.order_id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 400)
        self.assertIn("franja", res.json()["detail"].lower())

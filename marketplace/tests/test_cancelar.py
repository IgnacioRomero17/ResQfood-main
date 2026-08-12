from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta

from marketplace.models import Partner, Pack, Order

User = get_user_model()

class CancelarTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", password="pass123")
        self.other = User.objects.create_user(username="u2", password="pass123")
        owner = User.objects.create_user(username="owner", password="pass123")

        partner = Partner.objects.create(
            owner=owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local", direccion="x"
        )

        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=partner, titulo="Pack", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=500, stock=1,
            pickup_start=now - timedelta(hours=1),
            pickup_end=now + timedelta(hours=1),
        )

        self.client.login(username="u1", password="pass123")
        # Crear una reserva (usa tu endpoint reservar)
        reservar_url = reverse("pack-reservar", args=[self.pack.id])
        r = self.client.post(reservar_url)
        self.assertEqual(r.status_code, 201)
        self.order_id = r.json()["order_id"]

    def test_cancelar_ok_devuelve_stock(self):
        url = reverse("order-cancel", args=[self.order_id])  # action cancel en OrderViewSet
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200, res.content)
        o = Order.objects.get(id=self.order_id)
        self.assertEqual(o.estado, Order.Estado.CANCELADO)
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.stock, 1)  # se devolvió el stock

    def test_cancelar_no_propietario_forbidden(self):
        self.client.logout()
        self.client.login(username="u2", password="pass123")
        url = reverse("order-cancel", args=[self.order_id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 404)

    def test_cancelar_fuera_de_ventana_conflict(self):
        # Mover ventana para simular expirada
        p = Pack.objects.get(id=self.pack.id)
        p.pickup_end = timezone.now() - timedelta(minutes=1)
        p.save(update_fields=["pickup_end"])

        url = reverse("order-cancel", args=[self.order_id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 409)
        self.assertIn("no se puede cancelar", res.json()["detail"].lower())

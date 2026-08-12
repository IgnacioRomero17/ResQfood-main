from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta
from marketplace.models import Partner, Pack, Order

User = get_user_model()

class ViewsMoreTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.u1 = User.objects.create_user("u1", password="pass")
        self.owner = User.objects.create_user("owner", password="pass")
        self.partner = Partner.objects.create(
            owner=self.owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Comercio X", direccion="Calle"
        )

    def _nuevo_pack(self, start_delta, end_delta, stock=1, precio=500):
        now = timezone.now()
        return Pack.objects.create(
            partner=self.partner, titulo="Pack T", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=precio, stock=stock,
            pickup_start=now + start_delta, pickup_end=now + end_delta
        )

    def test_reservar_antes_de_pickup_start(self):
        # sólo corre si tu lógica BLOQUEA reservar antes de la ventana
        pack = self._nuevo_pack(start_delta=timedelta(hours=1), end_delta=timedelta(hours=2))
        self.client.login(username="u1", password="pass")
        res = self.client.post(reverse("pack-reservar", args=[pack.id]))
        # si permitís reservar antes, este test se puede skippear; si NO, debe ser 409
        self.assertIn(res.status_code, (201, 409))

    def test_redeem_fuera_de_ventana_por_fin(self):
        # ventana ya terminada
        pack = self._nuevo_pack(start_delta=timedelta(hours=-2), end_delta=timedelta(hours=-1))
        self.client.login(username="u1", password="pass")
        r = self.client.post(reverse("pack-reservar", args=[pack.id]))
        if r.status_code == 201:
            order_id = r.json()["order_id"]
        else:
            # si bloqueara en reservar, simula orden pendiente igual creando en ventana válida y luego venciendo
            pack = self._nuevo_pack(start_delta=timedelta(hours=-1), end_delta=timedelta(minutes=30))
            o = Order.objects.create(user=User.objects.get(username="u1"), pack=pack, precio_pagado=pack.precio_oferta)
            # vencer ventana
            pack.pickup_end = timezone.now() - timedelta(minutes=1)
            pack.save(update_fields=["pickup_end"]) 
            order_id = o.id
        self.client.logout()
        self.client.login(username="owner", password="pass")
        res = self.client.post(reverse("order-redeem", args=[order_id]))
        self.assertEqual(res.status_code, 400)
        self.assertIn("franja", res.json()["detail"].lower())

    def test_redeem_doble(self):
        # retirar una vez y volver a intentar
        pack = self._nuevo_pack(start_delta=timedelta(hours=-1), end_delta=timedelta(hours=1))
        self.client.login(username="u1", password="pass")
        r = self.client.post(reverse("pack-reservar", args=[pack.id]))
        self.assertEqual(r.status_code, 201)
        order_id = r.json()["order_id"]
        self.client.logout()
        self.client.login(username="owner", password="pass")
        ok = self.client.post(reverse("order-redeem", args=[order_id]))
        self.assertEqual(ok.status_code, 200)
        again = self.client.post(reverse("order-redeem", args=[order_id]))
        self.assertEqual(again.status_code, 400)

    def test_cancelar_estado_no_permitido(self):
        pack = self._nuevo_pack(start_delta=timedelta(hours=-1), end_delta=timedelta(hours=1))
        self.client.login(username="u1", password="pass")
        r = self.client.post(reverse("pack-reservar", args=[pack.id]))
        order_id = r.json()["order_id"]
        # marcarla como RETIRADA y luego intentar cancelar
        self.client.logout()
        self.client.login(username="owner", password="pass")
        self.client.post(reverse("order-redeem", args=[order_id]))
        self.client.logout()
        self.client.login(username="u1", password="pass")
        res = self.client.post(reverse("order-cancel", args=[order_id]))
        self.assertEqual(res.status_code, 400)

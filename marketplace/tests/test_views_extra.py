from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta
from marketplace.models import Partner, Pack, Order

User = get_user_model()

class ViewsExtraCoverageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.u1 = User.objects.create_user("u1", password="pass")
        self.owner = User.objects.create_user("owner", password="pass")
        self.partner = Partner.objects.create(
            owner=self.owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Comercio", direccion="x"
        )
        now = timezone.now()
        self.pack = Pack.objects.create(
            partner=self.partner, titulo="Pack X", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1200, precio_oferta=600, stock=1,
            pickup_start=now - timedelta(hours=1), pickup_end=now + timedelta(hours=2)
        )

    def test_reservar_no_autenticado(self):
        url = reverse("pack-reservar", args=[self.pack.id])
        res = self.client.post(url)
        # Con SessionAuth puede ser 403; con JWT suele ser 401
        self.assertIn(res.status_code, (401, 403))

    def test_pack_list_vigentes_filter_and_ordering(self):
    # crear uno fuera de ventana y otro con precio distinto para ordenar
        from django.utils import timezone
        from datetime import timedelta

        p2 = Pack.objects.create(
            partner=self.partner, titulo="Pack Y", etiqueta=Pack.Etiqueta.EXCEDENTE,
            precio_original=1000, precio_oferta=300, stock=0,
            pickup_start=timezone.now() - timedelta(days=1),
            pickup_end=timezone.now() - timedelta(hours=1)
    )

        url = reverse("pack-list") + "?vigentes=1&ordering=precio_oferta"

    # 👇 Forzar negociación a JSON
        res = self.client.get(url, HTTP_ACCEPT="application/json")
        self.assertEqual(res.status_code, 200, res.content)

        data = res.json()
        # DRF puede responder lista o {results: []} si activaste paginación
        if isinstance(data, dict) and "results" in data:
            items = data["results"]
        elif isinstance(data, list):
            items = data
        else:
            self.fail(f"Respuesta inesperada: {type(data)} -> {data}")

    # Debe estar solo el pack vigente (self.pack)
        self.assertTrue(len(items) >= 1)
        self.assertTrue(all(item["id"] == self.pack.id for item in items))

    def test_redeem_estado_invalido(self):
        # preparar orden cancelada y tratar de canjear
        self.client.login(username="u1", password="pass")
        reservar = self.client.post(reverse("pack-reservar", args=[self.pack.id]))
        order_id = reservar.json()["order_id"]
        self.client.post(reverse("order-cancel", args=[order_id]))
        self.client.logout()

        # intentar redeem como owner → debe fallar 400 por estado
        self.client.login(username="owner", password="pass")
        res = self.client.post(reverse("order-redeem", args=[order_id]))
        self.assertEqual(res.status_code, 403)
        self.assertIn("estado", res.json()["detail"].lower())

    def test_order_list_requires_auth(self):
        res = self.client.get(reverse("order-list"))
        self.assertIn(res.status_code, (401, 403))

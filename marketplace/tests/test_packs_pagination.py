from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from marketplace.models import Partner, Pack


User = get_user_model()


class PacksPaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pass")
        self.owner = User.objects.create_user("owner", password="pass")
        self.partner = Partner.objects.create(
            owner=self.owner,
            categoria=Partner.Categoria.RESTAURANTE,
            nombre="Comercio",
            direccion="x",
        )

    def _create_packs(self, total=15, vigente=True):
        now = timezone.now()
        for i in range(total):
            if vigente:
                pickup_start = now - timedelta(hours=1)
                pickup_end = now + timedelta(hours=2)
                stock = 1
            else:
                pickup_start = now - timedelta(days=2)
                pickup_end = now - timedelta(days=1)
                stock = 0
            Pack.objects.create(
                partner=self.partner,
                titulo=f"Pack {i}",
                etiqueta=Pack.Etiqueta.EXCEDENTE,
                precio_original=1000 + i,
                precio_oferta=100 + i,  # ascending by i
                stock=stock,
                pickup_start=pickup_start,
                pickup_end=pickup_end,
            )

    def test_pagination_shape_and_size(self):
        self._create_packs(total=15, vigente=True)
        url = reverse("pack-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # pagination envelope
        self.assertIn("count", data)
        self.assertIn("next", data)
        self.assertIn("previous", data)
        self.assertIn("results", data)
        # size
        self.assertEqual(len(data["results"]), 12)
        # second page
        res2 = self.client.get(url + "?page=2")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(len(data2["results"]), 3)
        self.assertEqual(data["count"], 15)
        self.assertIsNotNone(data["next"])  # has next
        self.assertIsNone(data["previous"])  # first page has no previous

    def test_ordering_precio_oferta_asc_desc(self):
        self._create_packs(total=15, vigente=True)
        # ascending
        url_asc = reverse("pack-list") + "?ordering=precio_oferta"
        res_asc = self.client.get(url_asc)
        self.assertEqual(res_asc.status_code, 200)
        prices_asc = [item["precio_oferta"] for item in res_asc.json()["results"]]
        self.assertEqual(prices_asc, sorted(prices_asc))
        # descending
        url_desc = reverse("pack-list") + "?ordering=-precio_oferta"
        res_desc = self.client.get(url_desc)
        self.assertEqual(res_desc.status_code, 200)
        prices_desc = [item["precio_oferta"] for item in res_desc.json()["results"]]
        self.assertEqual(prices_desc, sorted(prices_desc, reverse=True))

    def test_vigentes_filter_excludes_expired(self):
        # 10 vigentes + 5 expirados
        self._create_packs(total=10, vigente=True)
        self._create_packs(total=5, vigente=False)
        url = reverse("pack-list") + "?vigentes=1&ordering=precio_oferta"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # only vigentes counted
        self.assertEqual(data["count"], 10)
        # first page has up to 12 items, all with stock>0
        for item in data["results"]:
            self.assertGreater(item["stock"], 0)

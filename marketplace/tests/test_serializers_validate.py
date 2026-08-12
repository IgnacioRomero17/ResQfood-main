from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from marketplace.models import Partner
from marketplace.serializers import PackSerializer

User = get_user_model()

class SerializerValidateTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user("owner", password="pass")
        self.partner = Partner.objects.create(
            owner=owner, categoria=Partner.Categoria.RESTAURANTE,
            nombre="Local", direccion="x"
        )

    def test_pack_serializer_invalid_dates(self):
        now = timezone.now()
        payload = {
            "partner": self.partner.id,
            "titulo": "Pack Inválido",
            "etiqueta": "excedente",
            "precio_original": "1000.00",
            "precio_oferta": "500.00",
            "stock": 1,
            "pickup_start": (now + timedelta(hours=2)).isoformat(),
            "pickup_end":   (now + timedelta(hours=1)).isoformat(),  # end < start
        }
        s = PackSerializer(data=payload)
        # si tu serializer no valida esto, este test te mostrará dónde agregar la validación
        self.assertFalse(s.is_valid())

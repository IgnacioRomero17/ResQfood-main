from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from marketplace.models import Partner, Pack
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Crea partners y packs demo para poblar la home"

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true", help="Borra packs demo previos")
        parser.add_argument("--count", type=int, default=8, help="Cantidad de packs por partner")

    def handle(self, *args, **opts):
        User = get_user_model()
        user, _ = User.objects.get_or_create(username="demo_owner", defaults={"email": "demo@example.com"})
        if opts["fresh"]:
            Pack.objects.all().delete()
            self.stdout.write(self.style.WARNING("Borrados packs previos"))

        partners_data = [
            ("Supermercado El Sol", "supermercado"),
            ("Carnicería Don Juan", "restaurante"),
            ("Café Centro", "cafe"),
            ("Verdulería Verde", "verduleria"),
        ]

        partners = []
        for name, cat in partners_data:
            p, _ = Partner.objects.get_or_create(
                nombre=name,
                defaults={
                    "owner": user,
                    "categoria": cat,
                    "direccion": "Demo 123",
                    "slug": name.lower().replace(" ", "-")
                },
            )
            partners.append(p)

        now = timezone.now()
        for partner in partners:
            for i in range(1, opts["count"] + 1):
                title = f"Oferta especial #{i}"
                Pack.objects.get_or_create(
                    partner=partner,
                    titulo=title,
                    defaults={
                        "etiqueta": "excedente",
                        "precio_original": 2500,
                        "precio_oferta": 1890,
                        "stock": 5,
                        "pickup_start": now - timedelta(hours=1),
                        "pickup_end": now + timedelta(hours=6),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Packs demo creados/actualizados"))


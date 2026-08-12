from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from random import randint, choice, random
from marketplace.models import Partner, Pack
from django.contrib.auth import get_user_model


NAMES = [
    ("Verdulería La Hoja", "verduleria"),
    ("Panadería Trigo Fino", "panaderia"),
    ("Café & Deli Centro", "cafe"),
    ("Carnicería El Corte", "carniceria"),
    ("Heladería Polar", "heladeria"),
    ("Supermercado AhorraMás", "supermercado"),
    ("Almacén Doña Rosa", "almacen"),
    ("Pescadería Puerto", "pescaderia"),
    ("Dietética Natural", "dietetica"),
    ("Fábrica de Pastas Nero", "pastas"),
]


class Command(BaseCommand):
    help = "Agrega packs demo variados (sin borrar los existentes)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=40, help="Cantidad total de packs a crear")

    def handle(self, *args, **opts):
        User = get_user_model()
        owner, _ = User.objects.get_or_create(
            username="demo_owner",
            defaults={"email": "demo@example.com"},
        )

        partners = []
        # Asegura una base de partners diversos
        for name, cat in NAMES:
            p, _ = Partner.objects.get_or_create(
                nombre=name,
                defaults={
                    "owner": owner,
                    "categoria": cat,
                    "direccion": "Av. Demo 123",
                    "slug": name.lower().replace(" ", "-").replace("&", "y").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n"),
                },
            )
            partners.append(p)

        if not partners:
            self.stdout.write(self.style.WARNING("No hay partners disponibles"))
            return

        now = timezone.now()
        created = 0
        for i in range(opts["count"]):
            partner = partners[i % len(partners)]
            base = randint(1500, 6000)
            descuento = choice([10, 15, 20, 25])
            precio_original = float(base)
            precio_oferta = round(precio_original * (1 - descuento / 100.0))
            stock = randint(3, 12)

            start_delta_h = randint(-2, 1)
            end_delta_h = randint(4, 10)
            pickup_start = now + timedelta(hours=start_delta_h)
            pickup_end = now + timedelta(hours=end_delta_h)

            titulo = f"Pack demo #{timezone.now().strftime('%H%M%S')}-{i+1}"

            Pack.objects.create(
                partner=partner,
                titulo=titulo,
                etiqueta=choice(["excedente", "oferta", "últimas unidades"]),
                precio_original=precio_original,
                precio_oferta=precio_oferta,
                stock=stock,
                pickup_start=pickup_start,
                pickup_end=pickup_end,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Creados {created} packs demo"))


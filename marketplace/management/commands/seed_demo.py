from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
import os

from django.core.files.base import ContentFile
import requests

from marketplace.models import Partner, Pack, Order
from payments.models import Payment


User = get_user_model()


class Command(BaseCommand):
    help = "Crea datos de ejemplo para demo ResQFood"

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true", help="Borra datos existentes antes de crear")

    def handle(self, *args, **opts):
        now = timezone.now()

        if opts.get("fresh"):
            self.stdout.write("Limpiando datos previos...")
            Order.objects.all().delete()
            Payment.objects.all().delete()
            Pack.objects.all().delete()
            Partner.objects.all().delete()

        self.stdout.write("Creando usuarios demo...")
        customer, _ = User.objects.get_or_create(
            username="cliente_demo", defaults={"email": "demo@resqfood.com"}
        )
        customer.set_password("demo1234")
        customer.save()

        owner, _ = User.objects.get_or_create(
            username="partner_demo", defaults={"email": "partner@resqfood.com"}
        )
        owner.set_password("demo1234")
        owner.save()

        self.stdout.write("Creando comercios...")
        partners_data = [
            ("Panadería San José", "panaderia-san-jose", "Panadería artesanal", "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?q=80&w=800&auto=format&fit=crop"),
            ("Verdulería La Huerta", "verduleria-la-huerta", "Frutas y verduras frescas", "https://images.unsplash.com/photo-1542831371-29b0f74f9713?q=80&w=800&auto=format&fit=crop"),
            ("Café Aroma", "cafe-aroma", "Café de especialidad y pastelería", "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?q=80&w=800&auto=format&fit=crop"),
            ("Carnicería Don Juan", "carniceria-don-juan", "Cortes premium", "https://images.unsplash.com/photo-1601050690597-1c7505a0e30b?q=80&w=800&auto=format&fit=crop"),
            ("Supermercado El Sol", "supermercado-el-sol", "Productos variados y frescos", "https://images.unsplash.com/photo-1585325701954-3998d607c74f?q=80&w=800&auto=format&fit=crop"),
            ("Restaurante La Toscana", "restaurante-la-toscana", "Comida italiana casera", "https://images.unsplash.com/photo-1600891964599-f61ba0e24092?q=80&w=800&auto=format&fit=crop"),
        ]

        partners = []
        for name, slug, short, img_url in partners_data:
            p, _ = Partner.objects.get_or_create(
                slug=slug,
                defaults={
                    "owner": owner,
                    "categoria": Partner.Categoria.RESTAURANTE,
                    "nombre": name,
                    "direccion": f"Avenida {random.randint(1,200)}",
                    "short_description": short,
                },
            )
            # Descargar imagen de comercio
            try:
                if not p.imagen and img_url:
                    resp = requests.get(img_url, timeout=10)
                    if resp.ok:
                        filename = f"{slug}.jpg"
                        p.imagen.save(filename, ContentFile(resp.content), save=True)
            except Exception:
                pass
            partners.append(p)

        self.stdout.write("Creando packs...")
        etiquetas = [Pack.Etiqueta.EXCEDENTE, Pack.Etiqueta.POR_VENCER]
        pack_images = [
            "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1543353071-10c8ba85a904?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1526312426976-593c128eea40?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1460306855393-0410f61241c7?q=80&w=800&auto=format&fit=crop",
        ]
        for partner in partners:
            for i in range(random.randint(4, 6)):
                titulo = random.choice([
                    "Pack sorpresa", "Combo ahorro", "Caja del día",
                    "Oferta especial", "Selección gourmet", "Promo familiar",
                ])
                base = Decimal(random.randint(800, 2500))
                oferta = base * Decimal("0.8") if random.random() < 0.6 else base
                stock = random.randint(0, 15)
                start = now - timedelta(hours=random.randint(1, 6))
                end = now + timedelta(hours=random.randint(3, 10))
                pack, _ = Pack.objects.get_or_create(
                    partner=partner,
                    titulo=f"{titulo} #{i+1}",
                    defaults={
                        "etiqueta": random.choice(etiquetas),
                        "precio_original": base,
                        "precio_oferta": oferta,
                        "stock": stock,
                        "pickup_start": start,
                        "pickup_end": end,
                    },
                )
                # Imagen del pack
                try:
                    if not pack.imagen:
                        img_url = random.choice(pack_images)
                        resp = requests.get(img_url, timeout=10)
                        if resp.ok:
                            filename = f"pack_{partner.slug}_{i+1}.jpg"
                            pack.imagen.save(filename, ContentFile(resp.content), save=True)
                except Exception:
                    pass

        self.stdout.write("Creando pedidos de ejemplo...")
        packs = list(Pack.objects.all())
        created = 0
        for _ in range(8):
            if not packs:
                break
            pack = random.choice(packs)
            # Solo crear orden si está vigente (ventana activa) y con stock positivo
            if not (pack.stock > 0 and pack.pickup_end >= now):
                continue
            estado = random.choice([Order.Estado.PENDIENTE, Order.Estado.PAGADO, Order.Estado.RETIRADO])
            metodo = random.choice(["mp", "efectivo", "transferencia"])
            o = Order(user=customer, pack=pack, precio_pagado=pack.precio_oferta, estado=estado, metodo_pago=metodo)
            # Evitar descontar stock al crear; lo hará mark_paid si corresponde
            o._skip_stock = True
            o.save()
            if estado == Order.Estado.PAGADO:
                # marcar pago y crear Payment aprobado
                o.mark_paid()
                Payment.objects.create(order=o, provider=metodo, status="approved")
            created += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Datos demo creados. Partners:{len(partners)} Packs:{Pack.objects.count()} Orders:{created}"))

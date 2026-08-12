from datetime import timedelta
from random import randint, choice

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from marketplace.models import Partner, Pack

# Comercios demo (sin acentos para evitar problemas de codificación)
NAMES = [
    ("Bistro Mercado", "restaurante"),
    ("Restaurante La Estacion", "restaurante"),
    ("Verduleria La Hoja", "verduleria"),
    ("Panaderia Trigo Fino", "panaderia"),
    ("Cafe & Deli Centro", "cafe"),
    ("Carniceria El Corte", "carniceria"),
    ("Heladeria Polar", "heladeria"),
    ("Supermercado AhorraMas", "supermercado"),
    ("Almacen Dona Rosa", "almacen"),
    ("Pescaderia Puerto", "pescaderia"),
    ("Dietetica Natural", "dietetica"),
    ("Fabrica de Pastas Nero", "pastas"),
]

# Títulos de packs sugeridos por categoría para que se vean más cercanos a la foto
PACK_VARIANTS = {
    "verduleria": [
        "Bolsa de verduras de estacion",
        "Mix fresco para sopas y salteados",
        "Combo verde: hojas y raices",
        "Frutas y verduras para 3 comidas",
        "Pack grillado: zapallo, berenjena y cebolla",
    ],
    "panaderia": [
        "Pan de masa madre y facturas",
        "Pack dulce: medialunas y budin",
        "Panaderia variada de la tarde",
        "Pan de campo y prepizzas",
        "Brunch de panaderia: chipas y cuernitos",
    ],
    "cafe": [
        "Brunch para dos con cafe",
        "Box dulce: torta y cookies",
        "Sandwich gourmet con bebida",
        "Meriencafe: brownie y latte",
        "Box salado: focaccia y dips",
    ],
    "carniceria": [
        "Cortes seleccionados para la semana",
        "Mix de milanesas y carne picada",
        "Parrillero: chorizos y tira",
        "Pack guiso: roast beef y chorizo colorado",
        "Milanesas listas para freir",
    ],
    "heladeria": [
        "Helados artesanales 1Kg",
        "Torta helada variada",
        "Combo medio kilo y toppings",
        "Helado familiar con cucuruchos",
        "Postre helado con salsa y frutos secos",
    ],
    "supermercado": [
        "Canasta ahorro: secos y limpieza",
        "Pack desayuno y snacks",
        "Basicos de despensa y lacteos",
        "Kilo de pastas y salsas listas",
        "Pack ahorro: arroz, legumbres y leche",
    ],
    "almacen": [
        "Almacen variado: fideos y salsas",
        "Combo merienda: galletas y te",
        "Desayuno completo para la semana",
        "Pack merienda: mermelada y tostadas",
        "Dulce y salado para picar",
    ],
    "pescaderia": [
        "Filetes de pescado blanco",
        "Mix marino para paella",
        "Pescados del dia con limon",
        "Trio de filetes con especias",
        "Pescado para plancha con verduras",
    ],
    "dietetica": [
        "Mix saludable: frutos secos y semillas",
        "Desayuno fit: granola y miel",
        "Pack veggie con legumbres",
        "Snack saludable: mix dulce y salado",
        "Proteico: legumbres y semillas",
    ],
    "pastas": [
        "Pastas frescas surtidas",
        "Ravioles con salsa casera",
        "Hamburguesa doble mexicana",
        "Lasagna con salsa bolo",
        "Fideos cinta con pesto",
    ],
    "restaurante": [
        "Menu del dia con bebida",
        "Milanesa con pure y ensalada",
        "Burger gourmet con papas",
        "Pasta del chef con salsa especial",
        "Ensalada completa con proteina",
    ],
}


def ensure_demo_packs(min_count: int = 40):
    """Garantiza que existan al menos `min_count` packs demo."""
    # Refresca nombres de packs demo antiguos para que se vean más descriptivos
    rename_map = {"Nyoquis con queso rallado": "Hamburguesa doble mexicana"}
    for pack in Pack.objects.filter(
        models.Q(titulo__istartswith="Pack demo") | models.Q(titulo__in=rename_map.keys())
    ):
        cat = getattr(getattr(pack, "partner", None), "categoria", "")
        nuevo = rename_map.get(pack.titulo) or choice(PACK_VARIANTS.get(cat, ["Pack variado para llevar"]))
        pack.titulo = nuevo
        pack.save(update_fields=["titulo"])

    existing = Pack.objects.count()
    if existing >= min_count:
        return

    user_model = get_user_model()
    owner, _ = user_model.objects.get_or_create(
        username="demo_owner",
        defaults={"email": "demo@example.com"},
    )

    partners = list(Partner.objects.all())
    if not partners:
        for name, categoria in NAMES:
            partners.append(
                Partner.objects.create(
                    owner=owner,
                    nombre=name,
                    categoria=categoria,
                    direccion="Av. Demo 123",
                    slug=slugify(name)[:140],
                )
            )

    if not partners:
        return

    needed = min_count - existing
    now = timezone.now()
    etiquetas = ["excedente", "por_vencer"]

    def build_pack(partner, title_hint):
        precio_original = float(randint(1800, 6200))
        descuento = choice([10, 15, 20, 25])
        precio_oferta = round(precio_original * (1 - descuento / 100.0), 2)
        stock = randint(3, 12)
        pickup_start = now + timedelta(hours=randint(-2, 1))
        pickup_end = now + timedelta(hours=randint(4, 10))
        categoria = getattr(partner, "categoria", "")
        titulo = title_hint or choice(PACK_VARIANTS.get(categoria, ["Pack variado para llevar"]))
        return Pack.objects.create(
            partner=partner,
            titulo=titulo,
            etiqueta=choice(etiquetas),
            precio_original=precio_original,
            precio_oferta=precio_oferta,
            stock=stock,
            pickup_start=pickup_start,
            pickup_end=pickup_end,
        )

    # Asegurar que haya packs de restaurante para que la categoría no quede vacía
    if Pack.objects.filter(partner__categoria="restaurante").count() < 3:
        resto_partner = Partner.objects.filter(categoria="restaurante").first()
        if not resto_partner:
            resto_partner = Partner.objects.create(
                owner=owner,
                categoria="restaurante",
                nombre="Restaurante Demo",
                direccion="Av. Demo 789",
                slug=slugify("Restaurante Demo")[:140],
            )
        for _ in range(3):
            build_pack(resto_partner, None)

    for i in range(needed):
        partner = partners[i % len(partners)]
        categoria = getattr(partner, "categoria", "")
        titulo = choice(PACK_VARIANTS.get(categoria, ["Pack variado para llevar"]))
        build_pack(partner, titulo)

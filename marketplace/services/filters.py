from django.db.models import Q, F, Count
from django.utils import timezone

# Mapeo simple de categorías a nombre de Partner (sin migraciones reales)
CATEGORY_MAP = {
    "restaurantes": Q(partner__nombre__icontains="rest"),
    "super": Q(partner__nombre__icontains="super"),
    "kioscos": Q(partner__nombre__icontains="kios"),
    "helados": Q(partner__nombre__icontains="helad"),
    "cafes": Q(partner__nombre__icontains="café") | Q(partner__nombre__icontains="cafe"),
    "verdulerias": Q(partner__nombre__icontains="verdu"),
    "carnicerias": Q(partner__nombre__icontains="carni"),
    "fruterias": Q(partner__nombre__icontains="frut"),
}


def apply_pack_filters(qs, params):
    """
    Aplica filtros comunes a un queryset de Pack, usando nombres de campos reales.
    Filtros soportados vía query params:
      - categoria: slug (en CATEGORY_MAP)
      - oferta: '1'
      - stock: '1' (stock > 0)
      - abierto: '1' (pickup_start <= now <= pickup_end)
      - orden: 'nuevo' | 'mas-comprado' | 'precio-asc' | 'precio-desc'
    """
    now = timezone.now()

    # Base: activos por tiempo (vigencia aproximada) — sin campo 'vigente'
    qs = qs.filter(pickup_end__gte=now)

    cat = (params.get("categoria") or "").strip()
    if cat in CATEGORY_MAP:
        qs = qs.filter(CATEGORY_MAP[cat])

    if params.get("oferta") == "1":
        qs = qs.filter(precio_oferta__lt=F("precio_original"))

    if params.get("stock") == "1":
        qs = qs.filter(stock__gt=0)

    if params.get("abierto") == "1":
        qs = qs.filter(pickup_start__lte=now, pickup_end__gte=now)

    orden = (params.get("orden") or "").strip()
    if orden == "mas-comprado":
        # related_name 'orders' desde Order a Pack existe en el proyecto
        qs = qs.annotate(n=Count("orders")).order_by("-n", "-creado_at")
    elif orden == "precio-asc":
        qs = qs.order_by(F("precio_oferta").asc(nulls_last=True), F("precio_original").asc(nulls_last=True))
    elif orden == "precio-desc":
        qs = qs.order_by(F("precio_oferta").desc(nulls_last=True), F("precio_original").desc(nulls_last=True))
    else:
        qs = qs.order_by("-creado_at")

    return qs


def ui_filter_state(params):
    """Devuelve estado UI para marcar pills activas y el orden seleccionado."""
    return {
        "categoria": params.get("categoria", ""),
        "oferta": params.get("oferta") == "1",
        "stock": params.get("stock") == "1",
        "abierto": params.get("abierto") == "1",
        "orden": params.get("orden", "nuevo") or "nuevo",
        "categories": [
            {"slug": k, "title": t}
            for k, t in [
                ("restaurantes", "Restaurantes"), ("super", "Súper"), ("kioscos", "Kioscos"),
                ("helados", "Helados"), ("cafes", "Cafés"), ("verdulerias", "Verdulerías"),
                ("carnicerias", "Carnicerías"), ("fruterias", "Fruterías"),
            ]
        ],
    }


from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Count, F, Q
from marketplace.models import Partner, Pack
from marketplace.services.filters import apply_pack_filters, ui_filter_state
from marketplace.services.reminders import pending_orders_expiring
from marketplace.utils.images import stock_image_url

def home(request):
    base = Pack.objects.all()
    # Limit to 12 for at most two rows on desktop; CSS further clamps per viewport
    newest = apply_pack_filters(base, request.GET)[:12]

    params = request.GET.copy()
    params_mb = params.copy()
    params_mb["orden"] = params_mb.get("orden") or "mas-comprado"
    most_bought = apply_pack_filters(base, params_mb)[:12]

    params_of = params.copy()
    params_of["oferta"] = "1"
    offers = apply_pack_filters(base, params_of)[:12]

    # Category tiles: build stock URLs via helper (stable per slug)
    categories = [
    {"slug": "restaurantes", "title": "Restaurantes", "img_url": stock_image_url("restaurantes", "home-restaurantes"), "url": "/categoria/restaurantes/"},
    {"slug": "supermercados", "title": "Súper", "img_url": stock_image_url("supermercados", "home-supermercados"), "url": "/categoria/supermercados/"},
    {"slug": "helados", "title": "Helados", "img_url": stock_image_url("helados", "home-helados"), "url": "/categoria/helados/"},
    {"slug": "cafes", "title": "Café & Deli", "img_url": stock_image_url("cafes", "home-cafes"), "url": "/categoria/cafes/"},
    {"slug": "carniceria", "title": "Carnicerías", "img_url": stock_image_url("carniceria", "home-carniceria"), "url": "/categoria/carniceria/"},
    {"slug": "verduleria", "title": "Verdulerías", "img_url": stock_image_url("verduleria", "home-verduleria"), "url": "/categoria/verduleria/"},
    {"slug": "panaderia", "title": "Panaderías", "img_url": stock_image_url("panaderia", "home-panaderia"), "url": "/categoria/panaderia/"},
]

    ctx = {
        "filter_state": ui_filter_state(request.GET),
        "newest": newest,
        "most_bought": most_bought,
        "offers": offers,
        "categories": categories,
    }
    expiring_for_user = []
    try:
        if request.user.is_authenticated:
            expiring_for_user = list(pending_orders_expiring(user=request.user)[:3])
    except Exception:
        expiring_for_user = []
    ctx["expiring_orders"] = expiring_for_user
    # Render the enriched home as the main landing
    return render(request, "core/home_enriched.html", ctx)


def search(request):
    q = (request.GET.get("q") or "").strip()
    stock = request.GET.get("stock") == "1"
    oferta = request.GET.get("oferta") == "1"
    tipo = (request.GET.get("tipo") or "todos").strip()
    orden = (request.GET.get("orden") or "relevancia").strip()

    packs_qs = Pack.objects.none()
    partners_qs = Partner.objects.none()

    if q:
        # Nota: el modelo Partner de tu proyecto no tiene campo 'vigente'.
        # Filtramos por nombre solamente.
        partners_qs = Partner.objects.filter(nombre__icontains=q).order_by("nombre")

        # Pack tampoco requiere 'vigente'; aplicamos búsqueda por título/descripcion/partner
        packs_qs = Pack.objects.filter(
            Q(titulo__icontains=q) | Q(etiqueta__icontains=q) | Q(partner__nombre__icontains=q)
        )
        if stock:
            packs_qs = packs_qs.filter(stock__gt=0)
        if oferta:
            packs_qs = packs_qs.filter(precio_oferta__isnull=False, precio_oferta__lt=F("precio_original"))

        if orden == "precio-asc":
            packs_qs = packs_qs.order_by(F("precio_oferta").asc(nulls_last=True), F("precio_original").asc(nulls_last=True), "-creado_at")
        elif orden == "precio-desc":
            packs_qs = packs_qs.order_by(F("precio_oferta").desc(nulls_last=True), F("precio_original").desc(nulls_last=True), "-creado_at")
        elif orden == "reciente":
            packs_qs = packs_qs.order_by("-creado_at")
        else:
            packs_qs = packs_qs.order_by("-stock", "-creado_at")
    else:
        packs_qs = Pack.objects.none()
        partners_qs = Partner.objects.none()

    if tipo == "packs":
        partners_qs = Partner.objects.none()
    elif tipo == "partners":
        packs_qs = Pack.objects.none()

    from django.core.paginator import Paginator
    page_packs = Paginator(packs_qs, 24).get_page(request.GET.get("p_packs"))
    page_partners = Paginator(partners_qs, 12).get_page(request.GET.get("p_partners"))

    ctx = {
        "q": q,
        "stock": stock,
        "oferta": oferta,
        "tipo": tipo,
        "orden": orden,
        "page_packs": page_packs,
        "page_partners": page_partners,
    }
    return render(request, "core/search_results.html", ctx)

def error_404(request, exception):
    return render(request, "errors/404.html", status=404)

def error_500(request):
    return render(request, "errors/500.html", status=500)

def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)

from rest_framework import viewsets, permissions, decorators, response, status, filters
from .models import Partner, Pack, Order
from .serializers import PartnerSerializer, PackSerializer, OrderSerializer
from .models_cart import Cart, CartItem
from .permissions import IsPartner
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import F
from django.views.generic import DetailView
from django.http import HttpResponse, Http404
from django.core import signing
from io import BytesIO
import qrcode
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Max
from django.http import Http404
from django.db.models import F, Count
from marketplace.services.reminders import pending_orders_expiring

class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [permissions.IsAuthenticated]

class PackViewSet(viewsets.ModelViewSet):
    queryset = Pack.objects.select_related("partner").all()
    serializer_class = PackSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["titulo", "etiqueta", "partner__nombre"]
    ordering_fields = ["precio_oferta", "creado_at"]
    filterset_fields = ["etiqueta", "partner"]

    def get_queryset(self):
        qs = Pack.objects.select_related("partner").order_by("-creado_at")
        v = (self.request.query_params.get("vigentes") or "").lower()
        if v in ("1", "true", "yes"):
            now = timezone.now()
            qs = qs.filter(stock__gt=0, pickup_start__lte=now, pickup_end__gte=now)
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reservar(self, request, pk=None):
        user = request.user
        now = timezone.now()

        with transaction.atomic():
            # Lock de fila para evitar reservas simultÃ¡neas
            pack = Pack.objects.select_for_update().get(pk=pk)

            # Ventana de retiro y disponibilidad
            if pack.stock <= 0:
                return Response({"detail": "Sin stock disponible."}, status=status.HTTP_409_CONFLICT)
           # Permitimos reservar antes; solo bloqueamos si ya pasÃ³ la ventana
            if now > pack.pickup_end:
                return Response({"detail": "La franja de retiro ya expirÃ³."}, status=status.HTTP_409_CONFLICT)


            # Evitar duplicadas
            if Order.objects.filter(user=user, pack=pack, estado__in=[Order.Estado.PENDIENTE, Order.Estado.PAGADO]).exists():
                return Response({"detail": "Ya reservaste este pack."}, status=status.HTTP_409_CONFLICT)

            # Crear la orden (Order.save() validarÃ¡ y descontarÃ¡ stock atÃ³micamente)
            try:
                order = Order.objects.create(
                    user=user,
                    pack=pack,
                    precio_pagado=pack.precio_oferta,
                    estado=Order.Estado.PENDIENTE,
                )
            except ValidationError as e:
                # Si fallan las validaciones de clean() (p.ej. stock/ventana), devolver 409/400
                return Response({"detail": e.message}, status=status.HTTP_409_CONFLICT)

            # Refrescar pack para conocer el stock actualizado
            pack.refresh_from_db(fields=["stock"])

            return Response(
                {"detail": "Pack reservado âœ…", "order_id": order.id, "nuevo_stock": pack.stock},
                status=status.HTTP_201_CREATED,
            )


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("user", "pack", "pack__partner").all().order_by("-creado_at")
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Por defecto, cada usuario ve sus propias Ã³rdenes.
        # Para la acciÃ³n 'redeem' necesitamos poder acceder por pk sin filtrar por usuario
        # para que luego el propio mÃ©todo valide ownership y franja.
        qs = super().get_queryset()
        if getattr(self, "action", None) == "redeem":
            return qs
        return qs.filter(user=self.request.user)
    
    def get_serializer_class(self):
        # Para list y retrieve devolvemos el enriquecido
        if self.action in ["list", "retrieve"]:
            from .serializers import OrderLiteSerializer
            return OrderLiteSerializer
        return super().get_serializer_class()

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def redeem(self, request, pk=None):
        """
        Partner marca una orden como RETIRADA.
        Validaciones:
        - El usuario autenticado debe ser owner del partner del pack.
        - El horario actual debe estar dentro de la ventana pickup_start/pickup_end.
        - La orden debe estar PENDIENTE o PAGADO y el pack tener stock â€œconsumidoâ€ (ya manejado al crear).
        """
        try:
            order = (Order.objects
                     .select_related("pack", "pack__partner")
                     .get(pk=pk))
        except Order.DoesNotExist:
            return response.Response({"detail": "Orden inexistente."}, status=status.HTTP_404_NOT_FOUND)

        pack = order.pack
        partner = pack.partner

        # Verificar que el partner pertenece a este usuario
        if partner.owner_id != request.user.id:
            return response.Response({"detail": "No sos el dueÃ±o de este comercio."}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        if now < pack.pickup_start or now > pack.pickup_end:
            return response.Response({"detail": "Fuera de la franja de retiro."}, status=status.HTTP_400_BAD_REQUEST)

        if order.estado == Order.Estado.RETIRADO:
            return response.Response({"detail": "El pedido ya fue retirado."}, status=status.HTTP_400_BAD_REQUEST)
        if order.estado not in [Order.Estado.PENDIENTE, Order.Estado.PAGADO]:
            return response.Response({"detail": f"No se puede canjear una orden en estado {order.estado}."}, status=status.HTTP_400_BAD_REQUEST)

        order.estado = Order.Estado.RETIRADO
        order.save(update_fields=["estado"])
        return response.Response({"detail": "Orden marcada como RETIRADA âœ…"}, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["post"], url_path="verify-qr", permission_classes=[permissions.IsAuthenticated])
    def verify_qr(self, request):
        token = request.data.get("token")
        if not token:
            return response.Response({"detail": "Falta token."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = signing.loads(token)
            order_id = payload.get("order_id")
            order = (Order.objects
                     .select_related("pack", "pack__partner")
                     .get(pk=order_id))
        except Exception:
            return response.Response({"detail": "Token invÃ¡lido o orden inexistente."}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "order_id": order.id,
            "estado": order.estado,
            "pickup_start": order.pack.pickup_start,
            "pickup_end": order.pack.pickup_end,
            "partner_nombre": order.pack.partner.nombre,
        }
        return response.Response(data, status=status.HTTP_200_OK)
    
    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",          # <-- ruta explÃ­cita
        permission_classes=[permissions.IsAuthenticated]
    )
    
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.user_id != request.user.id:
            return response.Response({"detail": "No podÃ©s cancelar una orden de otro usuario."}, status=status.HTTP_403_FORBIDDEN)

        if order.estado not in [Order.Estado.PENDIENTE, Order.Estado.PAGADO]:
            return response.Response({"detail": f"No se puede cancelar una orden en estado {order.estado}."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if now > order.pack.pickup_end:
            return response.Response({"detail": "La franja ya expirÃ³, no se puede cancelar."}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            # Cambiar estado
            order.estado = Order.Estado.CANCELADO
            order.save(update_fields=["estado"])
            # Devolver stock
            type(order.pack).objects.filter(pk=order.pack_id).update(stock=F("stock") + 1)

        return response.Response({"detail": "Orden cancelada y stock devuelto âœ…"}, status=status.HTTP_200_OK)
    
@method_decorator(ensure_csrf_cookie, name='dispatch')
class MisReservasView(LoginRequiredMixin, ListView):
    template_name = "marketplace/mis_reservas.html"
    context_object_name = "orders"
    paginate_by = 12  # opcional

    def get_queryset(self):
        # Lo mismo que la API: solo mis Ã³rdenes, con joins del pack/partner
        return (
            Order.objects
            .select_related("pack", "pack__partner")
            .filter(user=self.request.user)
            .order_by("-creado_at")
        )
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["now"] = timezone.now()
        return ctx
    
   
class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = "marketplace/order_detail.html"
    context_object_name = "order"
    model = Order

    def get_queryset(self):
        # Solo dejo ver Ã³rdenes del usuario autenticado
        return (Order.objects
                .select_related("pack", "pack__partner")
                .filter(user=self.request.user))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from_q = (self.request.GET.get("from") or "").lower()
        ctx["from_cart"] = from_q == "cart"
        try:
            from payments.models import Payment
            ctx["payment_summary"] = Payment.summary_for_order(self.object)
        except Exception:
            ctx["payment_summary"] = {
                "exists": False,
                "provider": None,
                "status": None,
                "preference_id": None,
                "payment_id": None,
                "paid_at": None,
                "created_at": None,
            }
        # Reminder banner: show if pending and expiring in window
        try:
            o = self.object
            is_exp = False
            if o.estado == "pendiente" and self.request.user.is_authenticated:
                is_exp = pending_orders_expiring(user=self.request.user).filter(id=o.id).exists()
            ctx["is_expiring"] = bool(is_exp)
        except Exception:
            ctx["is_expiring"] = False
        return ctx


@login_required
def my_orders(request):
    user = request.user
    qs = (Order.objects.select_related("pack", "pack__partner")
          .filter(user=user))

    estado = (request.GET.get("estado") or "").strip()
    metodo = (request.GET.get("metodo") or "").strip()
    orden = (request.GET.get("orden") or "reciente").strip()

    if estado in ("pendiente", "pagado", "retirado", "cancelado"):
        qs = qs.filter(estado=estado)
    if metodo in ("mp", "efectivo", "transferencia"):
        qs = qs.filter(metodo_pago=metodo)

    if orden == "monto-asc":
        qs = qs.order_by("precio_pagado", "-creado_at")
    elif orden == "monto-desc":
        qs = qs.order_by("-precio_pagado", "-creado_at")
    else:
        qs = qs.order_by("-creado_at")

    page = Paginator(qs, 24).get_page(request.GET.get("page"))

    order_ids = [o.id for o in page.object_list]
    last_map = {}
    if order_ids:
        from payments.models import Payment
        latest = (Payment.objects
                  .filter(order_id__in=order_ids)
                  .values("order_id")
                  .annotate(last_created=Max("created_at")))
        keys = {(x["order_id"], x["last_created"]) for x in latest}
        if keys:
            pays = Payment.objects.filter(
                Q(order_id__in=order_ids) & Q(created_at__in=[t[1] for t in keys])
            )
            for p in pays:
                last_map[p.order_id] = p
    for o in page.object_list:
        o.last_payment = last_map.get(o.id)

    ctx = {
        "page": page,
        "filter_estado": estado,
        "filter_metodo": metodo,
        "orden": orden,
    }
    return render(request, "marketplace/my_orders.html", ctx)


# --- Categoría de packs (/categoria/<slug>/) ---
from django.http import Http404

CATEGORY_LABELS = {
    "restaurantes": "Restaurantes",
    "restaurante": "Restaurantes",
    "cafes": "Cafés",
    "cafe": "Cafés",
    "verduleria": "Verdulerías",
    "verdulerias": "Verdulerías",
    "carniceria": "Carnicerías",
    "carnicerias": "Carnicerías",
    "supermercados": "Supermercados",
    "supermercado": "Supermercados",
    "panaderia": "Panaderías",
    "panaderias": "Panaderías",
    "kiosco": "Kioscos",
    "kioscos": "Kioscos",
}

# Mapear slug recibido -> valor real en Partner.categoria
_CAT_VALUE = {
    "restaurantes": "restaurante",
    "restaurante": "restaurante",
    "cafes": "cafe",
    "cafe": "cafe",
    "verduleria": "verduleria",
    "verdulerias": "verduleria",
    "supermercados": "supermercado",
    "supermercado": "supermercado",
    "kiosco": "kiosco",
    "kioscos": "kiosco",
    # Si tu modelo no tiene carniceria/panaderia, permitir 404 amigable
    "carniceria": None,
    "carnicerias": None,
    "panaderia": None,
    "panaderias": None,
}


def categoria_list(request, slug: str):
    slug = (slug or "").strip().lower()
    titulo = CATEGORY_LABELS.get(slug)
    if not titulo:
        raise Http404("Categoría no encontrada")
    cat_value = _CAT_VALUE.get(slug)
    if not cat_value:
        # Si la categoría no existe en el modelo, devolver 404 clara
        raise Http404("Categoría no disponible")

    now = timezone.now()
    qs = Pack.objects.select_related("partner").filter(partner__categoria=cat_value)

    oferta = request.GET.get("oferta") == "1"
    stock = request.GET.get("stock") == "1"
    abierto = request.GET.get("abierto") == "1"

    if oferta:
        qs = qs.filter(precio_oferta__lt=F("precio_original"))
    if stock:
        qs = qs.filter(stock__gt=0)
    if abierto:
        qs = qs.filter(pickup_start__lte=now, pickup_end__gte=now)

    orden = (request.GET.get("orden") or "nuevo").strip()
    if orden == "precio-asc":
        qs = qs.order_by(
            F("precio_oferta").asc(nulls_last=True),
            F("precio_original").asc(nulls_last=True),
            "-creado_at",
        )
    elif orden == "precio-desc":
        qs = qs.order_by(
            F("precio_oferta").desc(nulls_last=True),
            F("precio_original").desc(nulls_last=True),
            "-creado_at",
        )
    elif orden == "mas-comprado":
        try:
            qs = qs.annotate(n=Count("orders")).order_by("-n", "-creado_at")
        except Exception:
            qs = qs.order_by("-creado_at")
    else:
        qs = qs.order_by("-creado_at")

    page = Paginator(qs, 24).get_page(request.GET.get("page"))
    ctx = {
        "slug": slug,
        "titulo": titulo,
        "page": page,
        "f_oferta": oferta,
        "f_stock": stock,
        "f_abierto": abierto,
        "orden": orden,
        "meta_title": f"{titulo} — ResQFood",
        "meta_desc": f"Packs en {titulo}. Ofertas, stock y horarios de retiro.",
    }
    return render(request, "marketplace/categoria_list.html", ctx)


def partner_detail(request, slug_or_id):
    now = timezone.now()
    partner = None
    try:
        partner = Partner.objects.get(slug=slug_or_id)
    except Partner.DoesNotExist:
        if str(slug_or_id).isdigit():
            partner = get_object_or_404(Partner, id=int(slug_or_id))
        else:
            raise Http404("Comercio no encontrado")

    qs = Pack.objects.filter(partner=partner)

    oferta = (request.GET.get("oferta") == "1")
    stock = (request.GET.get("stock") == "1")
    abierto = (request.GET.get("abierto") == "1")

    if oferta:
        qs = qs.filter(precio_oferta__lt=F("precio_original"))
    if stock:
        qs = qs.filter(stock__gt=0)
    if abierto:
        qs = qs.filter(pickup_start__lte=now, pickup_end__gte=now)

    orden = (request.GET.get("orden") or "nuevo").strip()
    if orden == "precio-asc":
        qs = qs.order_by(F("precio_oferta").asc(nulls_last=True), F("precio_original").asc(nulls_last=True), "-creado_at")
    elif orden == "precio-desc":
        qs = qs.order_by(F("precio_oferta").desc(nulls_last=True), F("precio_original").desc(nulls_last=True), "-creado_at")
    elif orden == "mas-comprado":
        qs = qs.annotate(n=Count("orders")).order_by("-n", "-creado_at")
    else:
        qs = qs.order_by("-creado_at")

    page = Paginator(qs, 24).get_page(request.GET.get("page"))

    is_open = qs.filter(pickup_start__lte=now, pickup_end__gte=now).exists()
    meta_title = f"{partner.nombre} — ResQFood"
    meta_desc = f"Ofertas y packs de {partner.nombre}. Retiro en local. Ver promociones, horarios y disponibilidad."

    ctx = {
        "partner": partner,
        "page": page,
        "f_oferta": oferta,
        "f_stock": stock,
        "f_abierto": abierto,
        "orden": orden,
        "meta_title": meta_title,
        "meta_desc": meta_desc,
        "is_open": is_open,
    }
    return render(request, "marketplace/partner_detail.html", ctx)

# --- endpoint que devuelve el PNG del QR (solo dueÃ±o) ---
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

@login_required
@require_GET
def order_qr_view(request, pk: int):
    try:
        order = (Order.objects
                 .select_related("pack", "pack__partner")
                 .get(pk=pk, user=request.user))
    except Order.DoesNotExist:
        raise Http404("Orden no encontrada")

    # Payload firmado (para evitar manipulaciones)
    # PodÃ©s incluir mÃ¡s campos si querÃ©s
    payload = {"order_id": order.id, "pack_id": order.pack_id}
    signed = signing.dumps(payload)  # incluye firma y timestamp

    # Generar QR como PNG
    img = qrcode.make(signed, box_size=8, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
def partner_redeem_page(request):
    return render(request, "partner/redeem.html")


class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_or_create_cart(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    def list(self, request):
        cart = self._get_or_create_cart(request)
        return response.Response(cart.to_dict())

    @decorators.action(detail=False, methods=["post"], url_path="add")
    def add(self, request):
        pack_id = request.data.get("pack_id")
        if not pack_id:
            return response.Response({"detail": "Falta pack_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pack = Pack.objects.select_related("partner").get(pk=pack_id)
        except Pack.DoesNotExist:
            return response.Response({"detail": "Pack inexistente"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if not (pack.stock > 0 and pack.pickup_start <= now <= pack.pickup_end):
            return response.Response({"detail": "El pack no est1 disponible"}, status=status.HTTP_400_BAD_REQUEST)

        cart = self._get_or_create_cart(request)
        existing_merchant = cart.merchant()
        if existing_merchant and existing_merchant.id != pack.partner_id:
            return response.Response({"detail": "El carrito admite solo packs del mismo comercio."}, status=status.HTTP_400_BAD_REQUEST)

        start_max, end_min = cart.window_intersection()
        if start_max and end_min:
            new_start = max(start_max, pack.pickup_start)
            new_end = min(end_min, pack.pickup_end)
            if new_start > new_end:
                return response.Response({"detail": "La ventana de retiro no es compatible con el carrito."}, status=status.HTTP_400_BAD_REQUEST)

        created = False
        if not CartItem.objects.filter(cart=cart, pack=pack).exists():
            CartItem.objects.create(cart=cart, pack=pack, quantity=1)
            created = True
        data = cart.to_dict()
        if not created:
            data["detail"] = "Ya estÃ¡ en el carrito"
        return response.Response(data)

    @decorators.action(detail=False, methods=["post"], url_path="remove")
    def remove(self, request):
        pack_id = request.data.get("pack_id")
        if not pack_id:
            return response.Response({"detail": "Falta pack_id"}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(request)
        CartItem.objects.filter(cart=cart, pack_id=pack_id).delete()
        return response.Response(cart.to_dict())

    @decorators.action(detail=False, methods=["post"], url_path="clear")
    def clear(self, request):
        cart = self._get_or_create_cart(request)
        CartItem.objects.filter(cart=cart).delete()
        return response.Response(cart.to_dict())

    @decorators.action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        cart = self._get_or_create_cart(request)
        items = list(cart.items)
        if not items:
            return response.Response({"detail": "El carrito estÃ¡ vacÃ­o"}, status=status.HTTP_400_BAD_REQUEST)

        pack_ids = [it.pack_id for it in items]
        with transaction.atomic():
            # lock packs for availability re-check
            packs_qs = (Pack.objects
                        .select_for_update()
                        .select_related("partner")
                        .filter(id__in=pack_ids))
            packs_by_id = {p.id: p for p in packs_qs}

            # validate single merchant
            partner_ids = {packs_by_id[pid].partner_id for pid in pack_ids}
            if len(partner_ids) != 1:
                return response.Response({"detail": "El carrito admite solo packs del mismo comercio."}, status=status.HTTP_400_BAD_REQUEST)

            # validate vigente and stock, and window intersection
            now = timezone.now()
            starts = []
            ends = []
            for it in items:
                p = packs_by_id.get(it.pack_id)
                if not p:
                    return response.Response({"detail": f"Pack {it.pack_id} inexistente"}, status=status.HTTP_400_BAD_REQUEST)
                if not (p.stock > 0 and p.pickup_start <= now <= p.pickup_end):
                    return response.Response({"detail": f"{p.titulo} ya no estÃ¡ disponible"}, status=status.HTTP_400_BAD_REQUEST)
                starts.append(p.pickup_start)
                ends.append(p.pickup_end)
            start_max = max(starts)
            end_min = min(ends)
            if start_max > end_min:
                return response.Response({"detail": "La ventana de retiro no es compatible entre los packs del carrito."}, status=status.HTTP_400_BAD_REQUEST)

            # Idempotency: if there are pending orders for this user that match current cart packs, reuse
            existing_qs = (Order.objects
                           .filter(user=request.user, estado=Order.Estado.PENDIENTE, pack_id__in=pack_ids))
            existing_pack_ids = set(existing_qs.values_list('pack_id', flat=True))
            if existing_pack_ids == set(pack_ids):
                first_id = existing_qs.order_by('id').values_list('id', flat=True).first()
                redirect_url = reverse('order_detail_public', args=[first_id]) + "?from=cart"
                return response.Response({"order_id": first_id, "detail_url": redirect_url}, status=status.HTTP_200_OK)

            # create one Order per cart item, but skip stock decrement until payment
            order_ids = []
            for it in items:
                p = packs_by_id[it.pack_id]
                o = Order(user=request.user, pack=p, precio_pagado=p.precio_oferta, estado=Order.Estado.PENDIENTE)
                o._skip_stock = True
                try:
                    o.save()
                except ValidationError as e:
                    transaction.set_rollback(True)
                    return response.Response({"detail": f"No se pudo crear la orden para {p.titulo}: {e.message}"}, status=status.HTTP_409_CONFLICT)
                order_ids.append(o.id)

        first = order_ids[0]
        try:
            redirect_url = reverse('order_detail_public', args=[first]) + "?from=cart"
        except Exception:
            redirect_url = reverse('order_detail', args=[first])
        return response.Response({"order_id": first, "detail_url": redirect_url}, status=status.HTTP_200_OK)


@login_required
def cart_page(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    pending_order_id = None
    partner = cart.merchant()
    if partner:
        po = (Order.objects
              .filter(user=request.user, estado=Order.Estado.PENDIENTE, pack__partner=partner)
              .order_by('id')
              .only('id')
              .first())
        if po:
            pending_order_id = po.id
    return render(request, "marketplace/cart.html", {"cart": cart, "pending_order_id": pending_order_id})

def merchant_detail(request, slug):
    now = timezone.now()
    partner = get_object_or_404(Partner, slug=slug)
    packs = (Pack.objects
             .filter(partner=partner, stock__gt=0, pickup_start__lte=now, pickup_end__gte=now)
             .order_by('-creado_at'))
    return render(request, 'marketplace/merchant_detail.html', { 'partner': partner, 'packs': packs })

def test_reservar_no_autenticado_rechazado(self):
    self.client.logout()
    url = reverse("pack-reservar", args=[self.pack.id])
    res = self.client.post(url)
    self.assertEqual(res.status_code, 401)

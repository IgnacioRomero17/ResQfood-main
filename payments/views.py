from django.views.decorators.http import require_POST, require_GET
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, Http404, HttpResponseServerError, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction
from django.utils import timezone
import uuid
import logging
from marketplace.models import Order
from .models import Payment
from django.urls import reverse
from django.conf import settings
from .gateways.mercadopago import create_mp_preference


@login_required
@require_POST
def mp_start(request, order_id: int):
    order = get_object_or_404(Order.objects.select_related('user'), pk=order_id)
    if order.user_id != request.user.id:
        return JsonResponse({"detail": "No puedes pagar un pedido de otro usuario."}, status=403)
    if order.estado != Order.Estado.PENDIENTE:
        return JsonResponse({"detail": "El pedido no está pendiente de pago."}, status=400)

    # Start payment depending on environment
    if settings.PAYMENTS_USE_LOCAL_MOCK:
        pref_id = str(uuid.uuid4())
        Payment.objects.create(order=order, provider='mp', preference_id=pref_id, status='pending')
        init_point = reverse('mp_mock', args=[order.id])
        return JsonResponse({"init_point": init_point, "preference_id": pref_id})

    try:
        pref = create_mp_preference(order)
        preference_id = pref.get("preference_id")
        if not preference_id:
            return HttpResponseServerError("MercadoPago preference creation failed")
        init_point = pref.get("sandbox_init_point") or pref.get("init_point")
        if not init_point:
            return HttpResponseServerError("MercadoPago init_point missing")
        payment = Payment.objects.create(order=order, provider='mp', preference_id=preference_id, status='pending')
        return JsonResponse({"init_point": init_point, "preference_id": preference_id, "payment_id": payment.id})
    except ValueError as e:
        return HttpResponseBadRequest(str(e))
    except Exception as e:
        logging.getLogger(__name__).exception("MP start failed")
        msg = "Payment service temporarily unavailable"
        if getattr(settings, "DEBUG", False):
            msg = f"Payment service error: {e}"
        return HttpResponseServerError(msg)


@require_POST
def mp_webhook(request):
    # Simplified sandbox webhook: expect JSON with {order_id, status}
    try:
        import json
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponse(status=400)
    order_id = payload.get('order_id')
    status = payload.get('status')
    if not order_id:
        return HttpResponse(status=400)
    if status not in ('approved', 'paid', 'authorized'):
        return HttpResponse(status=200)

    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
        # idempotent
        if order.estado == Order.Estado.PAGADO and order.stock_decremented:
            return HttpResponse(status=200)
        order.mark_paid()
    return HttpResponse(status=200)


@login_required
@require_GET
def mp_mock_checkout(request, order_id: int):
    """Very simple local mock page to simulate MP checkout in dev."""
    if not settings.PAYMENTS_USE_LOCAL_MOCK:
        raise Http404()
    order = get_object_or_404(Order.objects.select_related('user', 'pack', 'pack__partner'), pk=order_id)
    if order.user_id != request.user.id:
        return HttpResponseForbidden("No sos el dueño del pedido")
    return render(request, 'payments/mock_checkout.html', {"order": order})


@login_required
def mp_mock_approve(request, order_id: int):
    if not settings.PAYMENTS_USE_LOCAL_MOCK:
        raise Http404()
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
        if order.user_id != request.user.id:
            return HttpResponseForbidden("No sos el dueño del pedido")
        # If already paid just redirect
        if order.estado == Order.Estado.PAGADO:
            return redirect(reverse('order_detail_public', args=[order.id]) + "?from=cart")
        # idempotent safe mark paid
        order.mark_paid()
        # mark last payment approved if exists
        pay = Payment.last_for_order(order)
        if pay:
            pay.status = 'approved'
            pay.paid_at = timezone.now()
            pay.save(update_fields=['status', 'paid_at'])
    return redirect(reverse('order_detail_public', args=[order.id]) + "?from=cart")


@login_required
@require_GET
def payment_status(request, order_id: int):
    order = get_object_or_404(Order.objects.select_related('user'), pk=order_id)
    if order.user_id != request.user.id:
        return HttpResponseForbidden("No sos el dueño del pedido")
    data = {
        "order_id": order.id,
        "order_estado": order.estado,
        "paid_at": order.paid_at,
    }
    pay = Payment.last_for_order(order)
    data["payment"] = {
        "provider": getattr(pay, 'provider', None),
        "status": getattr(pay, 'status', None),
        "preference_id": getattr(pay, 'preference_id', None),
        "payment_id": None,
    }
    resp = JsonResponse(data)
    resp["Cache-Control"] = "no-store"
    return resp


# Mercado Pago return pages (require login)
@login_required
def mp_success(request):
    return render(request, "payments/return_success.html")


@login_required
def mp_pending(request):
    return render(request, "payments/return_pending.html")


@login_required
def mp_failure(request):
    return render(request, "payments/return_failure.html")


@login_required
@require_POST
def select_payment_method(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    if order.user_id != request.user.id:
        return HttpResponseForbidden("No sos el dueño del pedido")
    if order.estado != Order.Estado.PENDIENTE:
        return HttpResponseBadRequest("No podés cambiar el medio de pago en este estado")

    metodo = request.POST.get("metodo_pago")
    if metodo not in ("mp", "efectivo", "transferencia"):
        return HttpResponseBadRequest("Medio de pago inválido")

    if order.metodo_pago != metodo:
        order.metodo_pago = metodo
        order.save(update_fields=["metodo_pago"])

    return JsonResponse({"ok": True, "metodo_pago": order.metodo_pago}, status=200)


@login_required
@require_POST
def cash_start(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    if order.user_id != request.user.id:
        return HttpResponseForbidden("No sos el dueño del pedido")
    if order.estado != Order.Estado.PENDIENTE:
        return HttpResponseBadRequest("No podés iniciar pago en este estado")
    if order.metodo_pago != "efectivo":
        return HttpResponseBadRequest("El método seleccionado no es efectivo")

    pay = Payment.objects.filter(order=order, provider="efectivo").order_by("-created_at").first()
    if not pay or pay.status != "pending":
        pay = Payment.objects.create(order=order, provider="efectivo", status="pending")

    return JsonResponse({
        "ok": True,
        "provider": "efectivo",
        "status": pay.status,
        "message": "Reserva confirmada. Pagás en el retiro.",
    }, status=200)


@login_required
@require_POST
def transfer_start(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    if order.user_id != request.user.id:
        return HttpResponseForbidden("No sos el dueño del pedido")
    if order.estado != Order.Estado.PENDIENTE:
        return HttpResponseBadRequest("No podés iniciar pago en este estado")
    if order.metodo_pago != "transferencia":
        return HttpResponseBadRequest("El método seleccionado no es transferencia")

    pay = Payment.objects.filter(order=order, provider="transferencia").order_by("-created_at").first()
    if not pay or pay.status != "pending":
        pay = Payment.objects.create(order=order, provider="transferencia", status="pending")

    bank = {
        "alias": getattr(settings, "BANK_INFO_ALIAS", ""),
        "cbu": getattr(settings, "BANK_INFO_CBU", ""),
        "titular": getattr(settings, "BANK_INFO_TITULAR", ""),
        "cuit": getattr(settings, "BANK_INFO_CUIT", ""),
        "importe": None,
    }
    return JsonResponse({"ok": True, "provider": "transferencia", "status": pay.status, "bank": bank}, status=200)


@staff_member_required
@require_POST
def mark_payment_approved(request, payment_id: int):
    pay = get_object_or_404(Payment, pk=payment_id)
    try:
        changed = pay.mark_approved_manual()
        return JsonResponse({
            "ok": True,
            "payment_id": pay.id,
            "order_id": pay.order_id,
            "status": pay.status,
            "changed": bool(changed),
        })
    except Exception as e:
        return HttpResponseBadRequest(f"Error: {e}")

import json
import hmac
import hashlib
import uuid

from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings

from .models import Payment, WebhookLog
from marketplace.models import Order

try:
    import mercadopago  # type: ignore
except Exception:  # pragma: no cover
    mercadopago = None


def _verify_signature(request, parsed_body: dict) -> bool:
    """
    Basic verification: if MP_WEBHOOK_SECRET is set, compute HMAC-SHA256 over the raw body
    and compare to x-signature header (exact match or contained). If secret empty -> allow.
    """
    if not settings.MP_WEBHOOK_SECRET:
        return True
    sig = request.headers.get("x-signature", "")
    digest = hmac.new(
        settings.MP_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256
    ).hexdigest()
    return sig == digest or digest in sig


def _map_status(mp_status: str) -> str:
    s = (mp_status or "").lower()
    if s in ("approved",):
        return "approved"
    if s in ("pending", "in_process", "authorized"):
        return "pending"
    if s in ("rejected",):
        return "rejected"
    if s in ("cancelled", "canceled"):
        return "cancelled"
    if s in ("refunded",):
        return "refunded"
    if s in ("charged_back", "chargeback"):
        return "chargeback"
    return "pending"


@csrf_exempt
def mercadopago_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid json")

    if not _verify_signature(request, payload):
        return HttpResponseForbidden("invalid signature")

    request_id = request.headers.get("x-request-id") or ""
    # Idempotency guard at log level
    if request_id and WebhookLog.objects.filter(request_id=request_id).exists():
        return HttpResponse(status=200)

    # Build headers dict (case-insensitive mapping preserved as given by Django)
    headers_dict = {k: v for k, v in request.headers.items()}

    with transaction.atomic():
        # For missing request-id, generate a unique placeholder to avoid collisions
        log_request_id = request_id or f"no-id-{uuid.uuid4()}"
        WebhookLog.objects.create(request_id=log_request_id, headers=headers_dict, body=payload)

        data = payload.get("data") or {}
        mp_id = data.get("id") or payload.get("id")
        topic = (payload.get("type") or payload.get("topic") or "").lower()

        if not mp_id:
            return HttpResponse(status=200)

        # Lazy SDK init to allow tests to patch mercadopago
        if mercadopago is None:
            return HttpResponse(status=200)
        try:
            sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
            payment_data = None
            external_reference = None
            if topic in ("payment", "payments", ""):
                resp = sdk.payment().get(mp_id)
                payment_data = resp.get("response", {}) if isinstance(resp, dict) else {}
                external_reference = payment_data.get("external_reference")
            elif topic in ("merchant_order", "merchant_orders"):
                resp = sdk.merchant_order().get(mp_id)
                mo = resp.get("response", {}) if isinstance(resp, dict) else {}
                external_reference = mo.get("external_reference")
        except Exception:
            # Ack to prevent retries storm; no state change
            return HttpResponse(status=200)

        if not external_reference:
            return HttpResponse(status=200)

        try:
            order = Order.objects.select_for_update().get(pk=external_reference)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        pay_obj = Payment.objects.filter(order=order, provider="mp").order_by("-created_at").first()
        if not pay_obj:
            pay_obj = Payment.objects.create(order=order, provider="mp", status="pending")

        # Update provider fields
        pay_obj.payment_id = str(mp_id)
        pay_obj.raw_event = payload
        pay_obj.request_id = request_id or pay_obj.request_id  # keep if None
        pay_obj.save(update_fields=["payment_id", "raw_event", "request_id"])

        new_status = _map_status((payment_data or {}).get("status") if payment_data is not None else None)
        changed = pay_obj.apply_status(new_status)

        if new_status == "approved":
            order.mark_paid()

    return HttpResponse(status=200)


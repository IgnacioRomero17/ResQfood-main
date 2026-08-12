from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from marketplace.models import Order


def pending_orders_expiring(window_minutes=None, user=None):
    """
    Devuelve pedidos PENDIENTES cuyo pickup_end esté dentro de la ventana futura.
    Si 'user' está dado, filtra por ese usuario.
    """
    if window_minutes is None:
        window_minutes = getattr(settings, "REMINDER_WINDOW_MINUTES", 120)
    now = timezone.now()
    soon = now + timedelta(minutes=window_minutes)
    qs = Order.objects.select_related("pack", "pack__partner", "user").filter(
        estado="pendiente",
        pack__pickup_end__gt=now,
        pack__pickup_end__lte=soon,
    )
    if user is not None:
        qs = qs.filter(user=user)
    return qs


def send_reminder_email(order):
    """Envía (o simula) un email de recordatorio para un pedido."""
    user = getattr(order, "user", None)
    email = getattr(user, "email", "") if user is not None else ""
    if not email:
        return False
    subj = f"Recordatorio: tu pedido #{order.id} vence pronto"
    end = order.pack.pickup_end.strftime("%d/%m %H:%M")
    body = (
        f"¡Hola {getattr(user, 'username', '')}!\n\n"
        f"Tu pedido #{order.id} de {order.pack.partner.nombre} vence hoy a las {end}.\n"
        f"Título: {order.pack.titulo}\n"
        f"Monto: ${order.precio_pagado}\n\n"
        f"Podés completar el pago o ver el QR desde:\n"
        f"http://localhost:8000/orders/{order.id}/\n\n"
        f"— ResQFood"
    )
    sender = getattr(settings, "REMINDER_EMAIL_SENDER", "notificaciones@resqfood.local")
    try:
        send_mail(subj, body, sender, [email], fail_silently=True)
        return True
    except Exception:
        return False


from django.db import models
from django.conf import settings
from .models import Pack


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    creado_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart({self.user})"

    @property
    def items(self):
        return self.cart_items.select_related("pack", "pack__partner")

    def merchant(self):
        first = self.items.first()
        return first.pack.partner if first else None

    def item_count(self):
        return self.items.count()

    def total(self):
        from decimal import Decimal
        total = Decimal("0.00")
        for it in self.items:
            total += it.pack.precio_oferta * it.quantity
        return total

    def window_intersection(self):
        qs = self.items
        if not qs.exists():
            return (None, None)
        starts = [it.pack.pickup_start for it in qs]
        ends = [it.pack.pickup_end for it in qs]
        return (max(starts), min(ends))

    def to_dict(self):
        m = self.merchant()
        start_max, end_min = self.window_intersection()
        return {
            "merchant": m.nombre if m else None,
            "merchant_id": m.id if m else None,
            "item_count": self.item_count(),
            "total": str(self.total()),
            "window_start": start_max.isoformat() if start_max else None,
            "window_end": end_min.isoformat() if end_min else None,
            "items": [
                {
                    "pack_id": it.pack.id,
                    "titulo": it.pack.titulo,
                    "partner": it.pack.partner.nombre,
                    "precio": str(it.pack.precio_oferta),
                    "pickup_start": it.pack.pickup_start.isoformat(),
                    "pickup_end": it.pack.pickup_end.isoformat(),
                    "quantity": it.quantity,
                }
                for it in self.items
            ],
        }


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    agregado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "pack")

    def __str__(self):
        return f"{self.pack} x{self.quantity}"


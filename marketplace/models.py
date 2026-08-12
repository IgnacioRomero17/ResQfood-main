from django.db import models


# marketplace/models.py
from django.db import models
from django.conf import settings
from marketplace.utils.images import stock_image_url
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.db.models import Count, Q


class Partner(models.Model):
    class Categoria(models.TextChoices):
        RESTAURANTE = "restaurante", "Restaurante"
        VERDULERIA = "verduleria", "VerdulerÃ­a"
        SUPERMERCADO = "supermercado", "Supermercado"
        CAFE = "cafe", "CafÃ© & Deli"
        KIOSCO = "kiosco", "Kiosco"



    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="partners")
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.RESTAURANTE)
    nombre = models.CharField(max_length=120)
    direccion = models.CharField(max_length=200)
    creado_at = models.DateTimeField(auto_now_add=True)
    imagen = models.ImageField(upload_to="partners/", blank=True, null=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True, null=True)
    short_description = models.CharField(max_length=200, blank=True)


    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)[:140]
        super().save(*args, **kwargs)

    @classmethod
    def with_active_packs(cls):
        now = timezone.now()
        return (
            cls.objects
            .filter(packs__stock__gt=0, packs__pickup_start__lte=now, packs__pickup_end__gte=now)
            .annotate(activos=Count('packs', filter=Q(packs__stock__gt=0, packs__pickup_start__lte=now, packs__pickup_end__gte=now)))
            .distinct()
        )

    @property
    def image_or_stock_url(self):
        # Force stock if flag is enabled
        if getattr(settings, "USE_STOCK_IMAGES_FORCE_STOCK", False):
            slug = getattr(self, "categoria", "otros")
            return stock_image_url(slug, self.nombre or getattr(self, "slug", "") or str(self.pk))

        # Otherwise prefer real media if file exists
        if getattr(self, "imagen", None) and self.imagen:
            try:
                if self.imagen.name and self.imagen.storage.exists(self.imagen.name):
                    return self.imagen.url
            except Exception:
                pass

        if getattr(settings, "USE_STOCK_IMAGES_FOR_EMPTY", True):
            slug = getattr(self, "categoria", "otros")
            return stock_image_url(slug, self.nombre or getattr(self, "slug", "") or str(self.pk))
        return ""

class Pack(models.Model):
    class Etiqueta(models.TextChoices):
        POR_VENCER = "por_vencer", "Por vencer"
        EXCEDENTE = "excedente", "Excedente"

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="packs")
    titulo = models.CharField(max_length=140)
    etiqueta = models.CharField(max_length=20, choices=Etiqueta.choices)
    precio_original = models.DecimalField(max_digits=10, decimal_places=2)
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=1)
    pickup_start = models.DateTimeField()
    pickup_end = models.DateTimeField()
    creado_at = models.DateTimeField(auto_now_add=True)
    imagen = models.ImageField(upload_to="packs/", blank=True, null=True)  # ðŸ‘ˆ imagen opcional


    def __str__(self):
        return f"{self.titulo} - {self.partner.nombre}"

    @property
    def image_or_stock_url(self):
        if getattr(settings, "USE_STOCK_IMAGES_FORCE_STOCK", False):
            slug = getattr(self.partner, "categoria", "otros")
            key = f"{self.titulo}-{getattr(self.partner, 'nombre', '')}-{self.pk}"
            return stock_image_url(slug, key)

        if getattr(self, "imagen", None) and self.imagen:
            try:
                if self.imagen.name and self.imagen.storage.exists(self.imagen.name):
                    return self.imagen.url
            except Exception:
                pass

        if getattr(settings, "USE_STOCK_IMAGES_FOR_EMPTY", True):
            slug = getattr(self.partner, "categoria", "otros")
            key = f"{self.titulo}-{getattr(self.partner, 'nombre', '')}-{self.pk}"
            return stock_image_url(slug, key)
        return ""

# marketplace/models.py
class Order(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADO    = "pagado",    "Pagado"
        RETIRADO  = "retirado",  "Retirado"
        CANCELADO = "cancelado", "Cancelado"
        EXPIRADO  = "expirado",  "Expirado"

    METODO_PAGO_CHOICES = [
        ("mp", "Mercado Pago"),
        ("efectivo", "Efectivo al retirar"),
        ("transferencia", "Transferencia bancaria"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    pack = models.ForeignKey(Pack, on_delete=models.PROTECT, related_name="orders")
    precio_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    stock_decremented = models.BooleanField(default=False)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default="mp")

    def clean(self):
        """
        Validaciones SOLO aplican para la creaciÃ³n de la orden (reserva).
        """
        # Si se llama desde save() en creaciÃ³n, self._state.adding es True
        if self._state.adding:
            if self.pack.stock <= 0:
                raise ValidationError("No hay stock disponible para este pack.")
            if timezone.now() > self.pack.pickup_end:
                raise ValidationError("La franja de retiro de este pack ya expirÃ³.")
    def save(self, *args, **kwargs):
        creating = self._state.adding
        if creating:
            self.full_clean()  # valida al crear
        super().save(*args, **kwargs)
        # Descontar stock únicamente cuando la orden es NUEVA y no se omite (checkout)
        if creating and not getattr(self, "_skip_stock", False):
            Pack.objects.filter(pk=self.pack_id).update(stock=models.F("stock") - 1)
            type(self).objects.filter(pk=self.pk).update(stock_decremented=True)

    def mark_paid(self):
        if self.estado == self.Estado.PAGADO and self.stock_decremented:
            return
        if self.estado != self.Estado.PAGADO:
            self.estado = self.Estado.PAGADO
            self.paid_at = timezone.now()
            self.save(update_fields=["estado", "paid_at"])
        # decrement stock only once for orders created via checkout (no prior decrement)
        if not self.stock_decremented:
            Pack.objects.filter(pk=self.pack_id).update(stock=models.F("stock") - 1)
            type(self).objects.filter(pk=self.pk).update(stock_decremented=True)




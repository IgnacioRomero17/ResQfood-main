from rest_framework import serializers
from .models import Partner, Pack, Order
from django.contrib.auth import get_user_model


class PartnerSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = Partner
        fields = ["id", "nombre", "categoria", "imagen_url", "image_url"]

    def get_imagen_url(self, obj):
        # Legacy: real media URL if present
        try:
            if getattr(obj, "imagen", None) and obj.imagen and obj.imagen.name and obj.imagen.storage.exists(obj.imagen.name):
                request = self.context.get("request")
                url = obj.imagen.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    def get_image_url(self, obj):
        return obj.image_or_stock_url

class PackSerializer(serializers.ModelSerializer):
    partner_nombre = serializers.CharField(source="partner.nombre", read_only=True)
    partner_categoria = serializers.CharField(source="partner.categoria", read_only=True)
    partner_imagen_url = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()  # legacy media
    image_url = serializers.SerializerMethodField()   # stock-aware
    descripcion = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            "id","partner","partner_nombre","partner_categoria","titulo","descripcion","etiqueta",
            "precio_original","imagen_url","image_url","partner_imagen_url",
            "precio_oferta","stock","pickup_start","pickup_end","creado_at"
        ]
        
    def get_imagen_url(self, obj):
        try:
            if getattr(obj, "imagen", None) and obj.imagen and obj.imagen.name and obj.imagen.storage.exists(obj.imagen.name):
                request = self.context.get("request")
                url = obj.imagen.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    def get_image_url(self, obj):
        return obj.image_or_stock_url

    def get_descripcion(self, obj):
        """Descripcion generada en base a la categoria y titulo."""
        cat = getattr(obj.partner, "categoria", "") or ""
        title = getattr(obj, "titulo", "") or "Pack"
        templates = {
            "verduleria": f"{title} con verduras de estacion listas para cocinar en el dia.",
            "panaderia": f"{title} con panes, facturas y algo dulce para compartir.",
            "cafe": f"{title} combina opciones dulces y saladas para brunch o merienda.",
            "carniceria": f"{title} trae cortes listos para freezar o cocinar hoy.",
            "heladeria": f"{title} de helados artesanales, ideal para postre o merienda.",
            "supermercado": f"{title} con basicos de despensa para tu semana.",
            "almacen": f"{title} con productos secos y dulces para el dia a dia.",
            "pescaderia": f"{title} con filetes frescos listos para plancha u horno.",
            "dietetica": f"{title} con snacks y productos saludables para cualquier momento.",
            "pastas": f"{title} de pastas frescas listas para hervir y servir.",
        }
        return templates.get(cat, f"{title} listo para retirar en el local.")

    def get_partner_imagen_url(self, obj):
        try:
            if getattr(obj.partner, "imagen", None) and obj.partner.imagen and obj.partner.imagen.name and obj.partner.imagen.storage.exists(obj.partner.imagen.name):
                request = self.context.get("request")
                url = obj.partner.imagen.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return obj.partner.image_or_stock_url

    def validate(self, attrs):
        # Merge instance values on partial updates to compare effective values
        instance = getattr(self, "instance", None)

        def get_val(key):
            if key in attrs:
                return attrs.get(key)
            if instance is not None:
                return getattr(instance, key, None)
            return None

        pickup_start = get_val("pickup_start")
        pickup_end = get_val("pickup_end")
        precio_original = get_val("precio_original")
        precio_oferta = get_val("precio_oferta")

        errors = {}

        # Time window rule: end must be strictly greater than start
        if pickup_start is not None and pickup_end is not None:
            if not (pickup_end > pickup_start):
                errors["pickup_end"] = "pickup_end must be greater than pickup_start"

        # Price rule: oferta <= original
        if precio_original is not None and precio_oferta is not None:
            try:
                if precio_oferta > precio_original:
                    errors["precio_oferta"] = "precio_oferta must be <= precio_original"
            except TypeError:
                # Let DRF field-level validators handle type/format errors
                pass

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class OrderSerializer(serializers.ModelSerializer):
    pack_titulo = serializers.CharField(source="pack.titulo", read_only=True)

    class Meta:
        model = Order
        fields = ["id","user","pack","pack_titulo","precio_pagado","estado","creado_at",]
        read_only_fields = ["user","estado","creado_at"]
        
    
    def validate(self, attrs):
        pack = attrs.get("pack")
        if pack and pack.stock <= 0:
            raise serializers.ValidationError("No hay stock para este pack.")
        return attrs

    def create(self, validated_data):
        # setea el usuario que crea la orden
        validated_data["user"] = self.context["request"].user
        # precio pagado = precio oferta (por ahora)
        validated_data.setdefault("precio_pagado", validated_data["pack"].precio_oferta)
        order = super().create(validated_data)
        return order
    

class OrderLiteSerializer(serializers.ModelSerializer):
    pack_titulo = serializers.CharField(source="pack.titulo", read_only=True)
    partner_nombre = serializers.CharField(source="pack.partner.nombre", read_only=True)
    imagen = serializers.SerializerMethodField()
    pickup_start = serializers.DateTimeField(source="pack.pickup_start", read_only=True)
    pickup_end = serializers.DateTimeField(source="pack.pickup_end", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "estado", "precio_pagado", "creado_at",
            "pack", "pack_titulo", "partner_nombre", "imagen",
            "pickup_start", "pickup_end"
        ]


    def get_imagen(self, obj):
        return obj.pack.image_or_stock_url

User = get_user_model()


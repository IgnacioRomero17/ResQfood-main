from django.contrib import admin
from .models import Partner, Pack, Order


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "creado_at")
    search_fields = ("nombre", "categoria")

@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = ("titulo", "partner", "etiqueta", "precio_oferta", "stock", "pickup_start", "pickup_end", "creado_at")
    list_filter = ("etiqueta", "partner")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "pack", "precio_pagado", "estado", "creado_at")
    list_filter = ("estado",)
    search_fields = ("user__username", "pack__titulo")

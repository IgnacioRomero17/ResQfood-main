from django.contrib import admin, messages
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "status", "preference_id", "payment_id", "created_at")
    search_fields = ("id", "preference_id", "payment_id", "order__id")
    list_filter = ("provider", "status", "created_at")
    actions = ["marcar_como_aprobado"]

    @admin.action(description="Marcar pago seleccionado como APROBADO")
    def marcar_como_aprobado(self, request, queryset):
        count = 0
        for pay in queryset:
            try:
                changed = pay.mark_approved_manual()
                if changed:
                    count += 1
            except Exception as e:
                self.message_user(request, f"Error en Payment {pay.id}: {e}", level=messages.ERROR)
        if count:
            self.message_user(request, f"{count} pago(s) marcados como APROBADO.", level=messages.SUCCESS)


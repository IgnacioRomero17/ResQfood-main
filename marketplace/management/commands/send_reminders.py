from django.core.management.base import BaseCommand
from django.conf import settings
from marketplace.services.reminders import pending_orders_expiring, send_reminder_email


class Command(BaseCommand):
    help = "Envía emails de recordatorio para pedidos pendientes cuyo retiro vence pronto."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No envía, solo lista.")
        parser.add_argument("--limit", type=int, default=200, help="Máximo de recordatorios a procesar.")

    def handle(self, *args, **opts):
        if not getattr(settings, "REMINDER_ENABLED", True):
            self.stdout.write(self.style.WARNING("Recordatorios deshabilitados por settings.REMINDER_ENABLED=False"))
            return

        qs = pending_orders_expiring()[: opts["limit"]]
        if not qs.exists():
            self.stdout.write("No hay pedidos por vencer dentro de la ventana.")
            return

        sent = 0
        for o in qs:
            if opts["dry_run"]:
                self.stdout.write(f"[DRY] Pedido #{o.id} → {getattr(getattr(o, 'user', None), 'email', '-')}")
                continue
            ok = send_reminder_email(o)
            if ok:
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"✓ Enviado #{o.id}"))
            else:
                self.stdout.write(self.style.WARNING(f"✗ No se pudo enviar #{o.id}"))

        self.stdout.write(self.style.MIGRATE_HEADING(f"Total enviados: {sent}"))


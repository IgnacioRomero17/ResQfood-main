# marketplace/management/commands/expire_orders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from marketplace.models import Order

class Command(BaseCommand):
    help = "Marca como EXPIRADO las órdenes cuya franja de retiro ya terminó (pickup_end < now) y estén en PENDIENTE o PAGADO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cuántas órdenes expirarían sin modificar la base.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        estados_target = [Order.Estado.PENDIENTE, Order.Estado.PAGADO]

        qs = Order.objects.select_related("pack").filter(
            estado__in=estados_target,
            pack__pickup_end__lt=now,
        )

        count = qs.count()
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"[dry-run] Órdenes a expirar: {count}"))
            return

        with transaction.atomic():
            updated = qs.update(estado=Order.Estado.EXPIRADO)

        self.stdout.write(self.style.SUCCESS(f"Órdenes expiradas: {updated}"))

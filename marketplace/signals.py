from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_demo_packs(sender, app_config, **kwargs):
    if app_config.name != "marketplace":
        return
    if not getattr(settings, "AUTO_CREATE_DEMO_PACKS", True):
        return
    try:
        from .services.demo_seed import ensure_demo_packs

        ensure_demo_packs()
    except Exception:
        if settings.DEBUG:
            raise
        # En producción ignoramos errores silenciosamente

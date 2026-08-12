from django.apps import AppConfig
from django.conf import settings

class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        # Ensure additional models modules are imported so Django registers them
        from . import models_cart  # noqa: F401
        from . import signals  # noqa: F401
        if getattr(settings, "AUTO_CREATE_DEMO_PACKS", True):
            try:
                from .services.demo_seed import ensure_demo_packs

                ensure_demo_packs()
            except Exception:
                pass

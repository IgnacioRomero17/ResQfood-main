# resqfood/urls.py
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib import admin
from django.urls import path, include
from usuarios import views as user_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),          # <- home en "/"

    # FRONTEND (templates)
    path("packs/", include("packs.urls")),   # /packs/ -> HTML

    # API (todo lo de DRF va debajo de /api/)
    path("api/", include("api.urls")),       # /api/packs/ -> JSON
    path("api/payments/", include("payments.urls")),

    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),   
    path('', include('marketplace.urls')),
    path("webhooks/mercadopago/", include("payments.urls_webhooks")),

    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Cuenta de usuario
    path("mi-cuenta/", user_views.mi_cuenta, name="mi_cuenta"),
    path("mi-cuenta/cambiar-clave/", user_views.cambiar_clave, name="cambiar_clave"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
handler403 = 'core.views.error_403'


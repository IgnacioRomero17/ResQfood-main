# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from marketplace.views import PackViewSet

router = DefaultRouter()
router.register(r"packs", PackViewSet, basename="pack")

urlpatterns = [
    path("", include(router.urls)),  # con el include de resqfood -> /api/packs/
]

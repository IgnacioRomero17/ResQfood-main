from django.urls import path
from . import views_webhooks

urlpatterns = [
    path("", views_webhooks.mercadopago_webhook, name="mercadopago_webhook"),
]


from django.urls import path
from . import views

urlpatterns = [
    path('mp/start/<int:order_id>/', views.mp_start, name='mp_start'),
    path('mp/mock/<int:order_id>/', views.mp_mock_checkout, name='mp_mock'),
    path('mp/mock/<int:order_id>/approve/', views.mp_mock_approve, name='mp_mock_approve'),
    path('status/<int:order_id>/', views.payment_status, name='payment_status'),
]

# Return pages (require login)
urlpatterns += [
    path('success/', views.mp_success, name='mp_success'),
    path('pending/', views.mp_pending, name='mp_pending'),
    path('failure/', views.mp_failure, name='mp_failure'),
]

# Payment methods selection + non-MP flows
urlpatterns += [
    path('select-method/<int:order_id>/', views.select_payment_method, name='payments_select_method'),
    path('cash/start/<int:order_id>/', views.cash_start, name='payments_cash_start'),
    path('transfer/start/<int:order_id>/', views.transfer_start, name='payments_transfer_start'),
    path('admin/mark-approved/<int:payment_id>/', views.mark_payment_approved, name='payments_mark_approved'),
]

# Webhook is mounted at project level as /webhooks/mercadopago/

from django.urls import path
from .views import login_view, logout_view, dashboard_view
from .views import packs_view
from .views import packs_view, order_create_view
from .views import redeem_view
from .views import SignUpView


urlpatterns = [
    path("login/", login_view, name="login"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("packs/", packs_view, name="packs_view"),
    path("packs/<int:pack_id>/comprar/", order_create_view, name="order_create_view"),
    path("redeem/", redeem_view, name="redeem_view"),
    path("signup/", SignUpView.as_view(), name="signup"),
]

# core/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import home, search  # home y búsqueda

urlpatterns = [
    path("", home, name="home"),
    path("buscar/", search, name="search"),

    # Login personalizado (usa tu template y controla redirección si ya está autenticado)
    path("login/",
         LoginView.as_view(
             template_name="auth/login.html",
             redirect_authenticated_user=True  # ponlo en False si querés ver el form aun logueado
         ),
         name="login"),

    path("logout/", LogoutView.as_view(), name="logout"),
]

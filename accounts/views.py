import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login, logout as django_logout
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .utils import api_get, api_post
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase



class SignUpView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")  # o packs:list si preferís

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        return render(request, "accounts/login.html")

    username = request.POST.get("username")
    password = request.POST.get("password")

    user = authenticate(request, username=username, password=password)
    if not user:
        messages.error(request, "Usuario o contraseña inválidos.")
        return render(request, "accounts/login.html", status=401)

    # Logueo de sesión Django (para vistas server-side)
    django_login(request, user)

    # Generar tokens JWT sin hacer request HTTP
    refresh = TokenObtainPairSerializer.get_token(user)
    access = refresh.access_token

    # Guardar en sesión (servidor)
    request.session["jwt_access"] = str(access)
    request.session["jwt_refresh"] = str(refresh)

    messages.success(request, f"¡Bienvenido, {user.username}!")
    return redirect("dashboard")

def logout_view(request):
    django_logout(request)
    request.session.flush()
    messages.info(request, "Sesión cerrada.")
    return redirect("login")

@login_required
def dashboard_view(request):
    """
    Vista “protegida”: si llegaste acá, ya tenés sesión Django y tokens en session.
    Desde acá podés llamar a tu API /orders, /packs, etc. usando el access token del server.
    """
    access = request.session.get("jwt_access")
    # Ejemplo: mostrar el token parcialmente (debug) o usarlo para llamadas server-side
    ctx = {"user": request.user, "has_token": bool(access)}
    return render(request, "accounts/dashboard.html", ctx)

def packs_view(request):
    access = request.session.get("jwt_access")
    headers = {"Authorization": f"Bearer {access}"} if access else {}
    api_base = "http://127.0.0.1:8000"
    r = requests.get(f"{api_base}/packs/", headers=headers, timeout=5)
    data = r.json()
    return render(request, "accounts/packs.html", {"packs": data})

@login_required
def packs_view(request):
    # filtros simples opcionales ?search=... etc.
    q = request.GET.get("q")
    url = "/packs/"
    if q:
        url += f"?search={q}"
    resp = api_get(request.session, url)
    data = resp.json() if resp.ok else {"results": []}
    return render(request, "accounts/packs.html", {"packs": data.get("results", [])})

@login_required
def order_create_view(request, pack_id: int):
    if request.method != "POST":
        return redirect("packs_view")
    # crea la orden en la API (usa el token del usuario logueado)
    resp = api_post(request.session, "/orders/", json={"pack": pack_id})
    if resp.status_code == 201:
        messages.success(request, "¡Orden creada! Tenés una hora para retirar 🙂")
    else:
        try:
            err = resp.json()
        except Exception:
            err = {"detail": "Error inesperado"}
        messages.error(request, f"No se pudo crear la orden: {err}")
    return redirect("packs_view")

@login_required
@require_http_methods(["GET", "POST"])
def redeem_view(request):
    if request.method == "GET":
        return render(request, "accounts/redeem.html")

    order_id = request.POST.get("order_id")
    if not order_id:
        messages.error(request, "Ingresá un ID de orden.")
        return redirect("redeem_view")

    # POST /orders/{id}/redeem/
    resp = api_post(request.session, f"/orders/{order_id}/redeem/")
    if resp.ok:
        messages.success(request, f"Orden {order_id} marcada como RETIRADA ✅")
    else:
        try:
            err = resp.json()
        except Exception:
            err = {"detail": "Error inesperado"}
        messages.error(request, f"No se pudo canjear: {err}")
    return redirect("redeem_view")


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")  # o reverse_lazy("packs:list")


User = get_user_model()

class AccountsTests(TestCase):
    def test_register_user_ok(self):
        res = self.client.post(reverse("register"), {
            "username": "testuser",
            "password1": "pass1234",
            "password2": "pass1234"
        })
        self.assertEqual(res.status_code, 302)  # redirección post registro
        self.assertTrue(User.objects.filter(username="testuser").exists())
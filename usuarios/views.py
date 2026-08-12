from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django import forms

User = get_user_model()


class PerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
        }


@login_required
def mi_cuenta(request):
    user = request.user
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Perfil actualizado correctamente.")
            return redirect("mi_cuenta")
        else:
            messages.error(request, "❌ Por favor revisá los datos ingresados.")
    else:
        form = PerfilForm(instance=user)
    return render(request, "usuarios/mi_cuenta.html", {"form": form})


@login_required
def cambiar_clave(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "🔒 Contraseña actualizada correctamente.")
            return redirect("mi_cuenta")
        else:
            messages.error(request, "❌ Verificá los datos ingresados.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "usuarios/cambiar_clave.html", {"form": form})


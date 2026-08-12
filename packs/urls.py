from django.urls import path
from . import views

app_name = "packs"

urlpatterns = [
    path("", views.pack_list, name="list"),
    path("<int:pk>/", views.pack_detail, name="detail"),
]

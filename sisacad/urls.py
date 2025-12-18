from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse


def home(request):
    return HttpResponse("SISACAD activo — Bienvenido/a")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    # Módulo de usuarios (login/logout) usando NUESTRAS vistas
    path("accounts/", include("apps.users.urls", namespace="users")),

    # Si quieres, puedes exponer también las mismas URLs en /usuarios/
    # (no es obligatorio, puedes borrar esta línea si no la usas)
    # path("usuarios/", include("apps.users.urls", namespace="users")),

    path("academics/", include("apps.academics.urls", namespace="academics")),
    path("attendance/", include("apps.attendance.urls")),
]

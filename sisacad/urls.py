from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("SISACAD activo — Bienvenido/a")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("usuarios/", include("apps.users.urls", namespace="users")),
    path("academics/", include("apps.academics.urls", namespace="academics")),
    path("attendance/", include("apps.attendance.urls")),
    path("accounts/", include("django.contrib.auth.urls")),  # login/logout/password_*
]

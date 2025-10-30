from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return HttpResponse("SISACAD activo — Bienvenido/a")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("users/", include("apps.users.urls")),
    path("academics/", include("apps.academics.urls")),
    path("attendance/", include("apps.attendance.urls")),
]

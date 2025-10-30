# apps/attendance/urls.py
from django.urls import path

# Importamos vistas sin tocar modelos para que el módulo siempre cargue
from . import views_teacher, views_checkin

app_name = "attendance"

urlpatterns = [
    # Docente: ver sesiones del día
    path("teacher/today/", views_teacher.today_sessions, name="today_sessions"),
    # Estudiante: check-in a una sesión específica
    path("checkin/<int:session_id>/", views_checkin.checkin_form, name="checkin_form"),
]

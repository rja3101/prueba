from django.urls import path
from . import views_teacher

app_name = "teacher"

urlpatterns = [
    path("", views_teacher.teacher_dashboard, name="dashboard"),
    path("asistencia/", views_teacher.teacher_attendance, name="attendance"),
    path("notas/", views_teacher.teacher_grades, name="grades"),
    path("horario/", views_teacher.teacher_schedule, name="schedule"),
    path("ambientes/", views_teacher.teacher_rooms, name="rooms"),
]

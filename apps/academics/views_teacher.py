# apps/academics/views_teacher.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Avg, Min, Max

from .models import CourseGroup, Grade, Room, RoomReservation, Attendance


def _is_teacher(user):
    return hasattr(user, "role") and user.role and user.role.name.lower() == "docente"


# --- PANEL PRINCIPAL DEL DOCENTE ---
@login_required
def teacher_dashboard(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    # Grupos donde el docente dicta (docente está en Course.teacher)
    groups = CourseGroup.objects.filter(course__teacher=user).select_related("course")

    context = {
        "groups": groups,
    }
    return render(request, "teacher/dashboard.html", context)


# --- TOMAR ASISTENCIA (versión simple: lista de grupos) ---
@login_required
def teacher_attendance(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    groups = CourseGroup.objects.filter(course__teacher=user).select_related("course")

    context = {
        "groups": groups,
    }
    return render(request, "teacher/attendance.html", context)


# --- NOTAS Y ESTADÍSTICAS ---
@login_required
def teacher_grades(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    grades = (
        Grade.objects
        .select_related("assessment__course_group__course", "student")
        .filter(assessment__course_group__course__teacher=user)
    )

    stats = grades.aggregate(
        promedio=Avg("score"),
        minimo=Min("score"),
        maximo=Max("score"),
    )

    context = {
        "grades": grades,
        "stats": stats,
    }
    return render(request, "teacher/grades.html", context)


# --- HORARIO DEL DOCENTE (placeholder con lista de grupos) ---
@login_required
def teacher_schedule(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    groups = CourseGroup.objects.filter(course__teacher=user).select_related("course")

    context = {
        "groups": groups,
    }
    return render(request, "teacher/schedule.html", context)


# --- RESERVA DE AMBIENTES (vista básica) ---
@login_required
def teacher_rooms(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    rooms = Room.objects.all().order_by("floor", "number")
    my_reservations = RoomReservation.objects.filter(teacher=user).order_by("-date", "start_time")

    context = {
        "rooms": rooms,
        "reservations": my_reservations,
    }
    return render(request, "teacher/rooms.html", context)

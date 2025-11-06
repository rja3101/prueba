# apps/academics/views_student.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Prefetch

from .models import Course, CourseGroup, Enrollment, Grade


# -------------------------------------------
# UTILIDAD: Verifica si el usuario es alumno
# -------------------------------------------
def _is_student(user):
    return hasattr(user, "role") and user.role and user.role.name.lower() == "alumno"


# -------------------------------------------
# DASHBOARD PRINCIPAL
# -------------------------------------------
@login_required
def student_dashboard(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrollments = (
        Enrollment.objects
        .select_related("course_group__course")
        .filter(student=user)
        .order_by("course_group__course__code")
    )

    grades = (
        Grade.objects
        .select_related("assessment__course_group__course")
        .filter(student=user)
        .order_by("assessment__course_group__course__code", "assessment__title")
    )

    context = {
        "enrollments": enrollments[:5],
        "grades": grades[:5],
    }
    return render(request, "student/dashboard.html", context)


# -------------------------------------------
# MIS CURSOS
# -------------------------------------------
@login_required
def student_courses(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrollments = (
        Enrollment.objects
        .select_related("course_group__course")
        .filter(student=user)
        .order_by("course_group__course__code")
    )

    return render(request, "student/courses.html", {"enrollments": enrollments})


# -------------------------------------------
# MIS NOTAS
# -------------------------------------------
@login_required
def student_grades(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    grades = (
        Grade.objects
        .select_related("assessment__course_group__course")
        .filter(student=user)
        .order_by("assessment__course_group__course__code", "assessment__title")
    )

    return render(request, "student/grades.html", {"grades": grades})


# -------------------------------------------
# MATRICULARME EN CURSOS DISPONIBLES
# -------------------------------------------
@login_required
def student_offerings(request):
    """
    Muestra los CourseGroup disponibles para matrícula:
    Excluye aquellos en los que el alumno ya está matriculado.
    """
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrolled_group_ids = Enrollment.objects.filter(student=user).values_list("course_group_id", flat=True)

    groups = (
        CourseGroup.objects
        .select_related("course__teacher")  # 🔹 corrección aquí
        .exclude(id__in=enrolled_group_ids)
        .order_by("course__code")
    )

    return render(request, "student/offerings.html", {"groups": groups})


# -------------------------------------------
# MATRÍCULA DIRECTA EN UN CURSO
# -------------------------------------------
@login_required
def student_enroll(request, group_id):
    """
    Matricula al estudiante en un CourseGroup.
    Evita duplicados y redirige a la vista de cursos.
    """
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    try:
        group = CourseGroup.objects.select_related("course").get(id=group_id)
    except CourseGroup.DoesNotExist:
        return redirect("academics:student_offerings")

    # Evita duplicados
    Enrollment.objects.get_or_create(student=user, course_group=group)

    return redirect("academics:student_courses")


# -------------------------------------------
# HORARIO (placeholder)
# -------------------------------------------
@login_required
def student_schedule(request):
    """
    Versión simple: muestra las secciones en las que está matriculado el alumno.
    """
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrollments = (
        Enrollment.objects
        .select_related("course_group__course")
        .filter(student=user)
        .order_by("course_group__course__code")
    )

    return render(request, "student/schedule.html", {"enrollments": enrollments})

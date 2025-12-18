# apps/academics/urls.py
from django.urls import path
from .views_enrollment_cart import (
    offerings,
    cart_view,
    cart_add,
    cart_remove,
    cart_confirm,
)
from .views_import import import_students, import_enrollments
from .views_reports import occupancy_report, occupancy_csv
from .views_grades import import_grades, grades_csv
from .views_stats import group_stats_view
from . import views_student
from . import views_teacher


app_name = "academics"

urlpatterns = [
    path("offerings/", offerings, name="academics_offerings"),
    path("cart/", cart_view, name="academics_cart"),
    path("cart/add/<int:group_id>/", cart_add, name="academics_cart_add"),
    path("cart/remove/<int:group_id>/", cart_remove, name="academics_cart_remove"),
    path("cart/confirm/", cart_confirm, name="academics_cart_confirm"),

# --- DOCENTE ---
    path("docente/", views_teacher.teacher_dashboard, name="teacher_dashboard"),
    path("docente/asistencia/", views_teacher.teacher_attendance, name="teacher_attendance"),
    path("docente/notas/", views_teacher.teacher_grades, name="teacher_grades"),
    path("docente/horario/", views_teacher.teacher_schedule, name="teacher_schedule"),
    path("docente/ambientes/", views_teacher.teacher_rooms, name="teacher_rooms"),

    path(
        "docente/grupo/<int:group_id>/",
        views_teacher.teacher_course_detail,
        name="teacher_course_detail",
    ),

    path(
        "docente/tareas/<int:assignment_id>/",
        views_teacher.teacher_assignment_detail,
        name="teacher_assignment_detail",
    ),

    # --- SECRETARÍA ---
    path("secretary/import/students/", import_students, name="import_students"),
    path("secretary/import/enrollments/", import_enrollments, name="import_enrollments"),
    path("secretary/reports/occupancy/", occupancy_report, name="occupancy_report"),
    path("secretary/reports/occupancy.csv", occupancy_csv, name="occupancy_csv"),

    path("teacher/grades/import/<int:group_id>/", import_grades, name="import_grades"),
    path("group/<int:group_id>/grades.csv", grades_csv, name="grades_csv"),
    path("group/<int:group_id>/stats/view/", group_stats_view, name="coursegroup_stats_view"),

    # --- ALUMNO ---
    path("alumno/", views_student.student_dashboard, name="student_dashboard"),
    path("alumno/cursos/", views_student.student_courses, name="student_courses"),
    path(
        "alumno/cursos/<int:group_id>/",
        views_student.student_course_detail,
        name="student_course_detail",
    ),
    path("alumno/notas/", views_student.student_grades, name="student_grades"),
    path("alumno/ofertas/", views_student.student_offerings, name="student_offerings"),
    path(
        "alumno/ofertas/<int:group_id>/matricular/",
        views_student.student_enroll,
        name="student_enroll",
    ),
    path("alumno/horario/", views_student.student_schedule, name="student_schedule"),
    path("alumno/labs/", views_student.student_lab_offerings, name="student_lab_offerings"),
    path("alumno/labs/enroll/<int:lab_id>/", views_student.student_lab_enroll, name="student_lab_enroll"),
    path(
        "alumno/labs/unenroll/<int:lab_id>/",
        views_student.student_lab_unenroll,
        name="student_lab_unenroll",
    ),
    path(
        "alumno/tareas/<int:assignment_id>/",
        views_student.student_assignment_view,
        name="student_assignment_view",
    ),
]

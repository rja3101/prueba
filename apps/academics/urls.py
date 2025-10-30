# apps/academics/urls.py
from django.urls import path
from .views_enrollment_cart import offerings, cart_view, cart_add, cart_remove, cart_confirm
from .views_import import import_students, import_enrollments
from .views_reports import occupancy_report, occupancy_csv
from .views_grades import import_grades, grades_csv   # <- grades_csv lo agregamos abajo
from .views_stats import group_stats_view              # <- nombre EXACTO al tuyo

app_name = "academics"

urlpatterns = [
    path("offerings/", offerings, name="academics_offerings"),
    path("cart/", cart_view, name="academics_cart"),
    path("cart/add/<int:group_id>/", cart_add, name="academics_cart_add"),
    path("cart/remove/<int:group_id>/", cart_remove, name="academics_cart_remove"),
    path("cart/confirm/", cart_confirm, name="academics_cart_confirm"),

    path("secretary/import/students/", import_students, name="import_students"),
    path("secretary/import/enrollments/", import_enrollments, name="import_enrollments"),
    path("secretary/reports/occupancy/", occupancy_report, name="occupancy_report"),
    path("secretary/reports/occupancy.csv", occupancy_csv, name="occupancy_csv"),

    path("teacher/grades/import/<int:group_id>/", import_grades, name="import_grades"),
    path("group/<int:group_id>/grades.csv", grades_csv, name="grades_csv"),
    path("group/<int:group_id>/stats/view/", group_stats_view, name="coursegroup_stats_view"),
]

# apps/academics/views_reports.py
from __future__ import annotations
import csv
from io import StringIO

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.apps import apps

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def is_staff(user) -> bool:
    return bool(getattr(user, "is_staff", False))

def _gm(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

CourseGroup = _gm("academics", "CourseGroup")
Enrollment  = _gm("academics", "Enrollment")

def _get_enrolled_count_field():
    """Si el modelo tiene un campo calculado/propiedad, la usamos; si no, contamos en vivo."""
    # Campo típico en algunos diseños
    if CourseGroup and any(f.name == "enrolled_count" for f in CourseGroup._meta.get_fields()):
        return "enrolled_count"
    return None

# ────────────────────────────────────────────────────────────────
# Reporte HTML simple (sin template)
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def occupancy_report(request):
    if CourseGroup is None:
        return HttpResponse("<h1>Reporte de ocupación</h1><p>CourseGroup no está disponible.</p>", content_type="text/html")

    # Traemos datos básicos
    qs = CourseGroup.objects.select_related("course").all().order_by("course__code", "section")

    # Si no hay Enrollment o FK, usamos fallback
    enrolled_field = _get_enrolled_count_field()

    rows = []
    for g in qs:
        course_code = getattr(getattr(g, "course", None), "code", "")
        section     = getattr(g, "section", "")
        capacity    = getattr(g, "capacity", "")

        if enrolled_field:
            enrolled = getattr(g, enrolled_field, "")
        else:
            # Fallback contando en vivo
            if Enrollment:
                # FK puede llamarse group o course_group
                if any(f.name == "group" for f in Enrollment._meta.get_fields()):
                    enrolled = Enrollment.objects.filter(group=g).count()
                elif any(f.name == "course_group" for f in Enrollment._meta.get_fields()):
                    enrolled = Enrollment.objects.filter(course_group=g).count()
                else:
                    enrolled = ""
            else:
                enrolled = ""

        # available_slots (si existe) o calculado si capacity/enrolled son ints
        if hasattr(g, "available_slots"):
            available = getattr(g, "available_slots")
        else:
            try:
                available = int(capacity) - int(enrolled)
            except Exception:
                available = ""

        rows.append((course_code, section, capacity, enrolled, available))

    # Render HTML muy simple
    html = [
        "<h1>Reporte de ocupación</h1>",
        "<table border='1' cellpadding='4' cellspacing='0'>",
        "<tr><th>Curso</th><th>Sección</th><th>Capacidad</th><th>Matriculados</th><th>Disponibles</th></tr>",
    ]
    for r in rows:
        html.append(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>")
    html.append("</table>")
    return HttpResponse("\n".join(html), content_type="text/html")

# ────────────────────────────────────────────────────────────────
# CSV
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def occupancy_csv(request):
    if CourseGroup is None:
        resp = HttpResponse("course_code,section,capacity,enrolled,available\n", content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="occupancy.csv"'
        return resp

    qs = CourseGroup.objects.select_related("course").all().order_by("course__code", "section")
    enrolled_field = _get_enrolled_count_field()

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["course_code", "section", "capacity", "enrolled", "available"])

    for g in qs:
        course_code = getattr(getattr(g, "course", None), "code", "")
        section     = getattr(g, "section", "")
        capacity    = getattr(g, "capacity", "")

        if enrolled_field:
            enrolled = getattr(g, enrolled_field, "")
        else:
            if Enrollment:
                if any(f.name == "group" for f in Enrollment._meta.get_fields()):
                    enrolled = Enrollment.objects.filter(group=g).count()
                elif any(f.name == "course_group" for f in Enrollment._meta.get_fields()):
                    enrolled = Enrollment.objects.filter(course_group=g).count()
                else:
                    enrolled = ""
            else:
                enrolled = ""

        if hasattr(g, "available_slots"):
            available = getattr(g, "available_slots")
        else:
            try:
                available = int(capacity) - int(enrolled)
            except Exception:
                available = ""

        writer.writerow([course_code, section, capacity, enrolled, available])

    resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="occupancy.csv"'
    return resp

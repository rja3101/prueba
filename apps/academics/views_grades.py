# apps/academics/views_grades.py
import csv
from io import TextIOWrapper
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

# TODO: ajusta imports según tus modelos reales
from .models import CourseGroup, Assessment, Grade  # Grade: student, assessment, value; Assessment: group, name, weight

@login_required
def import_grades(request, group_id: int):
    """
    Carga de notas vía CSV con columnas:
    student_id, assessment_name, value
    """
    group = get_object_or_404(CourseGroup, id=group_id)

    if request.method == "POST" and request.FILES.get("file"):
        f = TextIOWrapper(request.FILES["file"].file, encoding=request.encoding or "utf-8")
        reader = csv.DictReader(f)
        inserted, updated, errors = 0, 0, 0

        for i, row in enumerate(reader, start=2):
            sid = row.get("student_id")
            aname = row.get("assessment_name")
            val = row.get("value")
            if not (sid and aname and val):
                errors += 1
                continue
            try:
                value = float(val)
            except ValueError:
                errors += 1
                continue

            assessment, _ = Assessment.objects.get_or_create(group=group, name=aname, defaults={"weight": 0})
            grade, created = Grade.objects.update_or_create(
                assessment=assessment, student_id=sid, defaults={"value": value}
            )
            inserted += int(created)
            updated += int(not created)

        messages.success(request, f"Importación completa: insertados {inserted}, actualizados {updated}, errores {errors}.")
        return redirect("academics:import_grades", group_id=group.id)

    return render(request, "teacher/import_grades.html", {"group": group})

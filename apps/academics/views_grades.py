# apps/academics/views_grades.py
from __future__ import annotations
import csv
from io import TextIOWrapper

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.shortcuts import redirect
from django.apps import apps

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def is_teacher(user) -> bool:
    """
    Ajusta esto a tu sistema de roles/permisos.
    Si manejas roles por atributo user.role.name == "Docente", úsalo;
    si no, por ahora acepta staff como "docente".
    """
    if hasattr(user, "role") and user.role and getattr(user.role, "name", "") in {"Docente", "Teacher"}:
        return True
    return bool(getattr(user, "is_staff", False))

def _gm(app_label: str, model_name: str):
    """get_model tolerante: None si no existe el modelo todavía."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

# Modelos (opcionales; el módulo debe importar aunque falten)
Grade = _gm("academics", "Grade")
Assessment = _gm("academics", "Assessment")
CourseGroup = _gm("academics", "CourseGroup")
User = _gm("auth", "User")

def _get_assessment_label(a) -> str:
    if a is None:
        return ""
    # title > name > str(a)
    return getattr(a, "title", getattr(a, "name", str(a)))

def _get_points_from_grade(g) -> str:
    if g is None:
        return ""
    if hasattr(g, "score"):
        return getattr(g, "score")
    if hasattr(g, "value"):
        return getattr(g, "value")
    return ""

def _find_assessment_by_group_and_label(group, label):
    """Busca Assessment por group + (title|name)==label."""
    if Assessment is None or group is None or not label:
        return None
    qs = Assessment.objects.filter(course_group=group)
    # probar por title y name
    a = qs.filter(title=label).first() if any(f.name == "title" for f in Assessment._meta.get_fields()) else None
    if a:
        return a
    a = qs.filter(name=label).first() if any(f.name == "name" for f in Assessment._meta.get_fields()) else None
    return a

def _get_group_or_404(group_id: int):
    if CourseGroup is None:
        raise Http404("CourseGroup no está disponible aún.")
    return CourseGroup.objects.filter(pk=group_id).first() or (_ for _ in ()).throw(Http404("Grupo no encontrado"))

# ────────────────────────────────────────────────────────────────
# 1) Exportar CSV de notas de un grupo
#    GET /academics/group/<group_id>/grades.csv
# columnas: student_username, assessment, points
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_teacher)
def grades_csv(request, group_id: int):
    group = _get_group_or_404(group_id)

    # Si no hay Grade o Assessment todavía, devolvemos solo cabecera
    if Grade is None or Assessment is None:
        resp = HttpResponse("student_username,assessment,points\n", content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="group_{group_id}_grades.csv"'
        return resp

    # Traer todas las calificaciones del grupo
    # Grade tiene FK a Assessment -> course_group
    grades_qs = Grade.objects.select_related("student", "assessment").filter(
        assessment__course_group=group
    )

    # Generar CSV
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="group_{group_id}_grades.csv"'
    writer = csv.writer(resp)
    writer.writerow(["student_username", "assessment", "points"])

    for g in grades_qs:
        student = getattr(g, "student", None)
        username = getattr(student, "username", str(student)) if student else ""
        assessment_label = _get_assessment_label(getattr(g, "assessment", None))
        points = _get_points_from_grade(g)
        writer.writerow([username, assessment_label, points])

    return resp

# ────────────────────────────────────────────────────────────────
# 2) Importar CSV de notas para un grupo
#    GET: formulario mínimo (HTML inline)
#    POST: espera un archivo CSV con columnas:
#          student_username, assessment, points
#    Intenta crear/actualizar Grade por (student, assessment).
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_teacher)
def import_grades(request, group_id: int):
    group = _get_group_or_404(group_id)

    # Si faltan modelos, no rompemos: avisamos y devolvemos formulario
    if request.method == "GET" or Grade is None or Assessment is None or User is None:
        if Grade is None or Assessment is None or User is None:
            msg = (
                "<p><strong>Advertencia:</strong> Los modelos necesarios (Grade/Assessment/User) "
                "no están disponibles aún. El formulario se muestra solo de referencia.</p>"
            )
        else:
            msg = ""
        return HttpResponse(
            f"""
            <h1>Importar notas — Grupo {group_id}</h1>
            {msg}
            <form method="post" enctype="multipart/form-data">
                <p><input type="file" name="file" accept=".csv" required></p>
                <p><button type="submit">Subir CSV</button></p>
            </form>
            <p>Formato esperado (cabeceras obligatorias): <code>student_username,assessment,points</code></p>
            """,
            content_type="text/html",
        )

    # POST real (con modelos disponibles)
    if request.method == "POST":
        if "file" not in request.FILES:
            messages.error(request, "No enviaste archivo CSV.")
            return redirect(request.path)

        # Decodificar CSV (asumimos UTF-8; ajusta si usas otro encoding)
        f = TextIOWrapper(request.FILES["file"].file, encoding="utf-8", newline="")
        reader = csv.DictReader(f)

        required = {"student_username", "assessment", "points"}
        if not required.issubset({h.strip() for h in reader.fieldnames or []}):
            messages.error(request, "CSV inválido: faltan cabeceras (student_username, assessment, points).")
            return redirect(request.path)

        created, updated, skipped = 0, 0, 0

        for row in reader:
            username = (row.get("student_username") or "").strip()
            assess_label = (row.get("assessment") or "").strip()
            points_raw = (row.get("points") or "").strip()

            if not username or not assess_label:
                skipped += 1
                continue

            # Buscar usuario
            student = User.objects.filter(username=username).first()
            if not student:
                skipped += 1
                continue

            # Buscar assessment por label y group
            assess = _find_assessment_by_group_and_label(group, assess_label)
            if not assess:
                skipped += 1
                continue

            # Preparar kwargs flexibles para Grade: score o value
            kwargs = {"student": student, "assessment": assess}
            try:
                # crear o actualizar
                g, was_created = Grade.objects.get_or_create(**kwargs)
                # setear puntos
                if hasattr(g, "score"):
                    g.score = _parse_points(points_raw)
                elif hasattr(g, "value"):
                    g.value = _parse_points(points_raw)
                g.save()
                created += int(was_created)
                updated += int(not was_created)
            except Exception:
                skipped += 1
                continue

        messages.success(
            request,
            f"Importación terminada. Nuevas: {created}, Actualizadas: {updated}, Omitidas: {skipped}.",
        )
        return redirect(request.path)

    # Método no permitido
    return HttpResponse(status=405)

# ────────────────────────────────────────────────────────────────
# Utilidades
# ────────────────────────────────────────────────────────────────
def _parse_points(s: str):
    """Convierte el valor de 'points' a número (float / int). Si falla, deja en blanco."""
    if s is None:
        return None
    s = s.strip().replace(",", ".")
    try:
        # intenta int si parece entero
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
        return float(s)
    except Exception:
        return None

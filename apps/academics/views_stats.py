# apps/academics/views_stats.py
from __future__ import annotations
from collections import Counter

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404
from django.apps import apps

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def is_teacher(user) -> bool:
    if hasattr(user, "role") and user.role and getattr(user.role, "name", "") in {"Docente", "Teacher"}:
        return True
    return bool(getattr(user, "is_staff", False))

def _gm(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

def _has_field(Model, name: str) -> bool:
    if Model is None:
        return False
    try:
        return any(f.name == name for f in Model._meta.get_fields())
    except Exception:
        return False

def _get_group_or_404(group_id: int):
    CG = _gm("academics", "CourseGroup")
    if CG is None:
        raise Http404("CourseGroup no está disponible.")
    obj = CG.objects.filter(pk=group_id).select_related("course").first()
    if not obj:
        raise Http404("Grupo no encontrado.")
    return obj

# Modelos (opcionales)
CourseGroup       = _gm("academics", "CourseGroup")
Enrollment        = _gm("academics", "Enrollment")
Grade             = _gm("academics", "Grade")
Assessment        = _gm("academics", "Assessment")
AttendanceRecord  = _gm("attendance", "AttendanceRecord")   # puede ser None si no existe la app
User              = _gm("auth", "User")

# ────────────────────────────────────────────────────────────────
# Funciones auxiliares de stats (robustas a esquemas distintos)
# ────────────────────────────────────────────────────────────────

def _enrolled_count_for_group(group) -> int:
    if Enrollment is None:
        return 0
    # FK puede llamarse group o course_group
    if _has_field(Enrollment, "group"):
        return Enrollment.objects.filter(group=group).count()
    if _has_field(Enrollment, "course_group"):
        return Enrollment.objects.filter(course_group=group).count()
    return 0

def _grades_for_group(group):
    """Devuelve lista de puntos (float/int) y etiquetas de evaluación para el grupo."""
    if Grade is None or Assessment is None:
        return []

    # Grades relacionados a assessments del grupo
    qs = Grade.objects.select_related("assessment").filter(
        **({"assessment__course_group": group} if _has_field(Assessment, "course_group") else {})
    )

    pts = []
    for g in qs:
        p = None
        if hasattr(g, "score"):
            p = g.score
        elif hasattr(g, "value"):
            p = g.value
        if p is not None:
            try:
                pts.append(float(p))
            except Exception:
                continue
    return pts

def _attendance_stats_for_group(group):
    """
    Retorna (total_registros, present_count) si existe AttendanceRecord.
    Intentamos varios nombres de campos comunes:
    - FK al grupo: group | course_group
    - campo 'present' o 'status' (str: 'present'/'absent', 'P'/'A', etc.)
    """
    if AttendanceRecord is None:
        return (0, 0)

    # filtro base por grupo (según FK real)
    if _has_field(AttendanceRecord, "group"):
        base = AttendanceRecord.objects.filter(group=group)
    elif _has_field(AttendanceRecord, "course_group"):
        base = AttendanceRecord.objects.filter(course_group=group)
    else:
        return (0, 0)

    total = base.count()
    if total == 0:
        return (0, 0)

    present = 0
    # Caso 1: booleano 'present'
    if _has_field(AttendanceRecord, "present"):
        present = base.filter(present=True).count()
        return (total, present)

    # Caso 2: 'status' con valores de texto
    if _has_field(AttendanceRecord, "status"):
        # Buscamos valores más comunes que signifiquen presente
        present_values = {"present", "Present", "P", "p", "1", "true", "True", "YES", "Yes", "si", "sí"}
        try:
            # Si el campo es CharField, hacemos conteo rápido en python
            vals = base.values_list("status", flat=True)
            for v in vals:
                if v is None:
                    continue
                if str(v).strip() in present_values:
                    present += 1
            return (total, present)
        except Exception:
            pass

    # Como fallback, 0 presentes
    return (total, 0)

# ────────────────────────────────────────────────────────────────
# Vista principal
# ────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_teacher)
def group_stats_view(request, group_id: int):
    group = _get_group_or_404(group_id)

    # Cabecera
    course_code = getattr(getattr(group, "course", None), "code", "")
    course_name = getattr(getattr(group, "course", None), "name", "")
    section     = getattr(group, "section", "")

    # Enrolled
    enrolled = _enrolled_count_for_group(group)

    # Attendance (si existe la app)
    att_total, att_present = _attendance_stats_for_group(group)
    att_rate = (att_present / att_total * 100.0) if att_total else None

    # Grades
    points = _grades_for_group(group)
    grade_count = len(points)
    avg = round(sum(points) / grade_count, 2) if grade_count else None
    mx  = round(max(points), 2) if grade_count else None
    mn  = round(min(points), 2) if grade_count else None

    # Distribución simple por decenas (0–10, 10–20, ... 90–100)
    buckets = Counter()
    for p in points:
        try:
            i = int(max(0, min(99, int(p)))) // 10  # 0..9
            buckets[i] += 1
        except Exception:
            continue

    # Render HTML simple (sin templates)
    html = [
        f"<h1>Estadísticas del Grupo {group_id}</h1>",
        f"<p><strong>Curso:</strong> {course_code} — {course_name} &nbsp; <strong>Sección:</strong> {section}</p>",
        "<h2>Resumen</h2>",
        "<ul>",
        f"<li><strong>Matriculados:</strong> {enrolled}</li>",
        f"<li><strong>Registros de asistencia:</strong> {att_total} " + (f"(presentes: {att_present}, tasa: {att_rate:.1f}%)" if att_total else "(N/D)") + "</li>",
        f"<li><strong>Notas cargadas:</strong> {grade_count} " + (f"(prom.: {avg}, máx.: {mx}, mín.: {mn})" if grade_count else "(N/D)") + "</li>",
        "</ul>",
        "<h2>Distribución de notas (por decenas)</h2>",
        "<table border='1' cellpadding='4' cellspacing='0'>",
        "<tr><th>Rango</th><th>Conteo</th></tr>",
    ]
    for i in range(10):
        lo = i * 10
        hi = lo + 10
        html.append(f"<tr><td>{lo}–{hi}</td><td>{buckets.get(i, 0)}</td></tr>")
    html.append("</table>")

    # Nota sobre fuentes de datos disponibles
    html.append("<p style='margin-top:1rem;color:#666'>"
                "(* Esta vista es tolerante: si no existe la app de asistencia o las evaluaciones, "
                "se muestran solo los datos disponibles.)</p>")

    return HttpResponse("\n".join(html), content_type="text/html")

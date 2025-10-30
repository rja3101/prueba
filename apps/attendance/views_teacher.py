# apps/attendance/views_teacher.py
from __future__ import annotations
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.apps import apps

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

def is_teacher(user) -> bool:
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))

Session     = _gm("attendance", "Session")
CourseGroup = _gm("academics", "CourseGroup")
Schedule    = _gm("attendance", "Schedule")  # por si tu Session->schedule->(course_group|group)

def _resolve_group_from_session(s):
    """
    Devuelve el CourseGroup (o None) a partir de una instancia de Session,
    probando varios caminos comunes:
      s.course_group
      s.group
      s.schedule.course_group
      s.schedule.group
    """
    # acceso directo
    if hasattr(s, "course_group") and getattr(s, "course_group", None):
        return getattr(s, "course_group")
    if hasattr(s, "group") and getattr(s, "group", None):
        return getattr(s, "group")

    # vía schedule
    sch = getattr(s, "schedule", None)
    if sch is not None:
        if hasattr(sch, "course_group") and getattr(sch, "course_group", None):
            return getattr(sch, "course_group")
        if hasattr(sch, "group") and getattr(sch, "group", None):
            return getattr(sch, "group")

    return None

@login_required
@user_passes_test(is_teacher)
def today_sessions(request):
    """
    Lista sencilla de sesiones del día para el docente.
    Evita select_related con nombres inexistentes y resuelve la relación al grupo dinámicamente.
    """
    today = date.today()

    if Session is None:
        return HttpResponse(
            f"<h1>Sesiones de hoy ({today})</h1><p>No está definido el modelo Session.</p>",
            content_type="text/html",
        )

    # Base queryset
    qs = Session.objects.all()

    # Si hay campo date, filtramos por hoy
    try:
        if _has_field(Session, "date"):
            qs = qs.filter(date=today)
    except Exception:
        pass

    # No usar select_related con 'course_group' porque en tu caso el campo es 'schedule'.
    # Si existe 'schedule', sí podemos optimizar:
    try:
        if _has_field(Session, "schedule"):
            qs = qs.select_related("schedule")
    except Exception:
        pass

    # Construimos filas resolviendo el group en tiempo de ejecución
    rows = []
    for s in qs:
        grp = _resolve_group_from_session(s)
        course = getattr(grp, "course", None)
        code = getattr(course, "code", "")
        sec  = getattr(grp, "section", "")
        hour = getattr(s, "start_time", "") if hasattr(s, "start_time") else ""
        gid  = getattr(grp, "id", "")
        rows.append((s.pk, code, sec, hour, gid))

    html = [
        f"<h1>Sesiones de hoy ({today})</h1>",
        "<table border='1' cellpadding='4' cellspacing='0'>",
        "<tr><th>ID</th><th>Curso</th><th>Sección</th><th>Hora</th><th>GrupoID</th></tr>",
    ]
    for r in rows:
        html.append(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>")
    html.append("</table>")
    return HttpResponse("\n".join(html), content_type="text/html")

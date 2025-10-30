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

def is_teacher(user) -> bool:
    if hasattr(user, "role") and user.role and getattr(user.role, "name", "") in {"Docente", "Teacher"}:
        return True
    return bool(getattr(user, "is_staff", False))

Session = _gm("attendance", "Session")
CourseGroup = _gm("academics", "CourseGroup")

@login_required
@user_passes_test(is_teacher)
def today_sessions(request):
    """
    Listado simple de sesiones del día para el docente (sin templates).
    Si no existen los modelos, la vista sigue cargando con un mensaje.
    """
    today = date.today()
    if Session is None:
        return HttpResponse(
            f"<h1>Sesiones de hoy ({today})</h1><p>No está definido el modelo Session.</p>",
            content_type="text/html",
        )

    # Intentamos filtrar por fecha si hay campo date/start_time; si no, listamos todo.
    qs = Session.objects.all()
    # campo 'date' típico
    try:
        if any(f.name == "date" for f in Session._meta.get_fields()):
            qs = qs.filter(date=today)
    except Exception:
        pass

    qs = qs.select_related("course_group") if CourseGroup else qs

    rows = []
    for s in qs:
        gid = getattr(getattr(s, "course_group", None), "id", "")
        code = getattr(getattr(getattr(s, "course_group", None), "course", None), "code", "")
        sec = getattr(getattr(s, "course_group", None), "section", "")
        hour = getattr(s, "start_time", "") if hasattr(s, "start_time") else ""
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

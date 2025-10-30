# apps/attendance/views_checkin.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.shortcuts import redirect
from django.apps import apps

# ── helpers ─────────────────────────────────────────────────────
def _gm(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

def is_student(user) -> bool:
    # Ajusta a tu esquema real de roles. Mientras, acepta usuarios logueados.
    if hasattr(user, "role") and user.role and getattr(user.role, "name", "") in {"Alumno", "Student"}:
        return True
    return True

Session = _gm("attendance", "Session")
AttendanceRecord = _gm("attendance", "AttendanceRecord")
CourseGroup = _gm("academics", "CourseGroup")

def _get_session_or_404(session_id: int):
    if Session is None:
        raise Http404("El modelo Session no está disponible aún.")
    obj = Session.objects.filter(pk=session_id).first()
    if not obj:
        raise Http404("Sesión no encontrada.")
    return obj

# ── vistas ──────────────────────────────────────────────────────
@login_required
@user_passes_test(is_student)
def checkin_form(request, session_id: int):
    """
    Formulario mínimo de check-in (sin template).
    Si no hay modelos, mostramos un HTML explicativo pero no rompemos.
    """
    if request.method == "GET":
        if Session is None or AttendanceRecord is None:
            return HttpResponse(
                "<h1>Check-in</h1>"
                "<p>No están definidos los modelos de asistencia (Session/AttendanceRecord). "
                "La vista está operativa, pero el registro real se activará cuando existan los modelos.</p>",
                content_type="text/html",
            )
        # GET real con modelos
        ses = _get_session_or_404(session_id)
        return HttpResponse(
            f"""
            <h1>Check-in — Sesión {ses.pk}</h1>
            <form method="post">
                <p>Estado:
                    <select name="status" required>
                        <option value="present">Presente</option>
                        <option value="absent">Ausente</option>
                        <option value="late">Tarde</option>
                    </select>
                </p>
                <p><button type="submit">Registrar</button></p>
            </form>
            """,
            content_type="text/html",
        )

    # POST
    if request.method == "POST":
        if Session is None or AttendanceRecord is None:
            messages.error(request, "Aún no hay modelos de asistencia configurados.")
            return redirect(request.path)

        ses = _get_session_or_404(session_id)
        status = (request.POST.get("status") or "").strip() or "present"
        # Crear registro de asistencia tolerante a campos
        ar = AttendanceRecord()
        # FKs tolerantes según cómo se llamen
        if any(f.name == "session" for f in AttendanceRecord._meta.get_fields()):
            setattr(ar, "session", ses)
        if any(f.name == "group" for f in AttendanceRecord._meta.get_fields()) and getattr(ses, "group_id", None):
            setattr(ar, "group", getattr(ses, "group"))
        if any(f.name == "course_group" for f in AttendanceRecord._meta.get_fields()) and getattr(ses, "course_group_id", None):
            setattr(ar, "course_group", getattr(ses, "course_group"))
        # alumno actual
        if any(f.name == "student" for f in AttendanceRecord._meta.get_fields()):
            setattr(ar, "student", request.user)
        # status / present
        if any(f.name == "status" for f in AttendanceRecord._meta.get_fields()):
            setattr(ar, "status", status)
        if any(f.name == "present" for f in AttendanceRecord._meta.get_fields()):
            setattr(ar, "present", status in {"present", "Present", "P", "p", "true", "True", "1"})
        # timestamp si existe se deja que auto_now_add lo maneje; si no, ignoramos

        try:
            ar.save()
            messages.success(request, "Asistencia registrada.")
        except Exception as e:
            messages.error(request, f"No se pudo registrar asistencia: {e}")

        return redirect(request.path)

    return HttpResponse(status=405)

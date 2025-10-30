# apps/attendance/views_checkin.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import HttpResponseBadRequest

# TODO: ajusta import según tus modelos reales
from .models import Session, AttendanceRecord  # AttendanceRecord: session, student, status, timestamp
from academics.models import Enrollment  # Enrollment: student, group

@login_required
def checkin_list(request, session_id: int):
    """Pantalla para marcar asistencia de una sesión (lista de matriculados en el grupo)."""
    session = get_object_or_404(Session, id=session_id, teacher=request.user)
    # Trae estudiantes del grupo de la sesión
    enrollments = (
        Enrollment.objects
        .filter(group=session.group)
        .select_related("student")
        .order_by("student__last_name", "student__first_name")
    )

    # Mapa rápido de asistencias existentes
    existing = {
        (ar.student_id): ar
        for ar in AttendanceRecord.objects.filter(session=session).select_related("student")
    }

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        status = request.POST.get("status")  # "present", "late", "absent"
        if not student_id or status not in {"present", "late", "absent"}:
            return HttpResponseBadRequest("Datos inválidos")

        ar, _created = AttendanceRecord.objects.update_or_create(
            session=session,
            student_id=student_id,
            defaults={"status": status, "timestamp": timezone.now()},
        )
        return redirect("attendance:checkin", session_id=session.id)

    ctx = {
        "session": session,
        "enrollments": enrollments,
        "existing": existing,
    }
    return render(request, "teacher/checkin_list.html", ctx)

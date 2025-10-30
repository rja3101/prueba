# apps/attendance/views_teacher.py
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from datetime import date

# TODO: ajusta import según tus modelos reales
from .models import Session  # fields esperados: start_datetime, group, room, course, teacher

@login_required
def today_sessions(request):
    """Lista las sesiones de HOY para el docente autenticado."""
    tz_now = timezone.localtime()
    today = tz_now.date()
    # Si tu modelo usa 'date' + 'start_time', cambia el filtro.
    sessions = (
        Session.objects
        .filter(teacher=request.user, start_datetime__date=today)
        .select_related("group", "course")  # ajusta a tus FKs reales
        .order_by("start_datetime")
    )
    ctx = {"today": today, "sessions": sessions}
    return render(request, "teacher/today_sessions.html", ctx)

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Session, Attendance
def is_teacher(u): return hasattr(u,"role") and u.role and u.role.name=="Docente"
TOL_MINUTES = 15

@login_required @user_passes_test(is_teacher)
def check_in(request, session_id:int):
    if request.method != "POST": return redirect("teacher_today")
    s = get_object_or_404(Session.objects.select_related("schedule"), pk=session_id)
    now = timezone.now()
    start_dt = timezone.make_aware(timezone.datetime.combine(s.date, s.schedule.start_time))
    if now > start_dt + timezone.timedelta(minutes=TOL_MINUTES):
        messages.error(request,"Fuera de la ventana de tolerancia."); return redirect("teacher_today")
    ip = request.META.get("REMOTE_ADDR","0.0.0.0")
    Attendance.objects.get_or_create(session=s, student=request.user, defaults={"ip_address":ip, "entry_time":now})
    messages.success(request, "Asistencia registrada.")
    return redirect("teacher_today")

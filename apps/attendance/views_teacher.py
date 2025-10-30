from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone
from .models import Session
def is_teacher(u): return hasattr(u,"role") and u.role and u.role.name=="Docente"

@login_required @user_passes_test(is_teacher)
def today_sessions(request):
    today = timezone.localdate()
    qs = (Session.objects.select_related("schedule","schedule__course_group","schedule__course_group__course")
          .filter(schedule__course_group__course__teacher=request.user, date=today)
          .order_by("schedule__start_time"))
    return render(request,"teacher/today_sessions.html",{"sessions":qs,"today":today})

from django.http import HttpResponse
from django.utils import timezone

def attendance_index(request):
    ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    return HttpResponse(f"Módulo Asistencia OK — Tu IP: {ip} — {now}")

# apps/academics/views_import.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.apps import apps

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def is_staff(user) -> bool:
    """Permite solo personal de Secretaría / staff."""
    return bool(getattr(user, "is_staff", False))

def _gm(app_label: str, model_name: str):
    """get_model tolerante: None si no existe el modelo todavía."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

# Carga opcional de modelos (no son obligatorios para que el módulo importe)
User = _gm("auth", "User")
Enrollment = _gm("academics", "Enrollment")
CourseGroup = _gm("academics", "CourseGroup")

# ────────────────────────────────────────────────────────────────
# Importar estudiantes (placeholder funcional)
# ────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def import_students(request):
    """
    Placeholder seguro para importación de estudiantes.
    - No requiere templates.
    - No truena si faltan modelos.
    - Para POST: simplemente confirma recepción del archivo.
    """
    if request.method == "POST":
        if request.FILES:
            messages.success(request, "Archivo recibido. (Procesamiento pendiente)")
        else:
            messages.warning(request, "No se envió archivo. (Envía un CSV en multipart/form-data)")
        return redirect(request.path)

    # GET simple (sin template)
    return HttpResponse(
        "<h1>Importar estudiantes</h1>"
        "<p>Endpoint operativo. Envía un POST con archivo CSV (multipart/form-data).</p>",
        content_type="text/html",
    )

# ────────────────────────────────────────────────────────────────
# Importar matrículas (placeholder funcional)
# ────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def import_enrollments(request):
    """
    Placeholder seguro para importación de matrículas.
    - No requiere templates.
    - No truena si faltan modelos (Enrollment/CourseGroup pueden ser None).
    """
    if request.method == "POST":
        if request.FILES:
            # Aquí iría tu parsing CSV real; por ahora solo confirmamos recepción
            messages.success(request, "Archivo de matrículas recibido. (Procesamiento pendiente)")
        else:
            messages.warning(request, "No se envió archivo. (Envía un CSV en multipart/form-data)")
        return redirect(request.path)

    # GET simple (sin template)
    return HttpResponse(
        "<h1>Importar matrículas</h1>"
        "<p>Endpoint operativo. Envía un POST con archivo CSV (multipart/form-data).</p>",
        content_type="text/html",
    )

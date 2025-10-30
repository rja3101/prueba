# apps/academics/views_enrollment_cart.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.apps import apps

# ────────────────────────────────────────────────────────────────
# Carga segura de modelos (no revienta si el modelo no existe)
# ────────────────────────────────────────────────────────────────
try:
    Term = apps.get_model("academics", "Term")           # puede no existir aún
except LookupError:
    Term = None

try:
    CourseGroup = apps.get_model("academics", "CourseGroup")
except LookupError:
    CourseGroup = None

# ────────────────────────────────────────────────────────────────
# Servicios de matrícula (asumimos que existen en tu app)
# ────────────────────────────────────────────────────────────────
from .services_enrollment import (
    add_to_cart,
    remove_from_cart,
    confirm_cart,
    get_or_create_cart,
)

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def is_student(u):
    """Ajusta esta verificación a tu sistema de roles/permisos."""
    return hasattr(u, "role") and u.role and getattr(u.role, "name", "") == "Alumno"

def _current_term():
    """Devuelve el último término si existe; si no, None (no rompe)."""
    if Term is None:
        return None
    try:
        return Term.objects.order_by("-start_date").first()
    except Exception:
        return None

def _redir(name_with_ns: str, name_no_ns: str, *args, **kwargs):
    """
    Redirección tolerante a namespace.
    Intenta 'academics:...' y, si no existe, usa el nombre simple.
    """
    try:
        return redirect(reverse(name_with_ns, args=args, kwargs=kwargs))
    except Exception:
        return redirect(reverse(name_no_ns, args=args, kwargs=kwargs))

# ────────────────────────────────────────────────────────────────
# Ofertas (catálogo de grupos con carrito)
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_student)
def offerings(request):
    term = _current_term()
    if CourseGroup is None:
        messages.error(request, "El modelo CourseGroup aún no está disponible.")
        return _redir("academics:academics_cart", "academics_cart")

    # Query base
    qs = CourseGroup.objects.select_related("course")
    # Si tu modelo Course tiene FK hacia teacher/professor, lo intentamos:
    try:
        qs = qs.select_related("course__teacher")
    except Exception:
        pass

    groups = qs.order_by("course__code", "section")
    return render(request, "academics/offerings_cart.html", {"groups": groups, "term": term})

# ────────────────────────────────────────────────────────────────
# Ver carrito
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_student)
def cart_view(request):
    term = _current_term()
    if term is None:
        messages.warning(request, "Aún no hay término activo configurado.")
    cart = get_or_create_cart(request.user, term)
    # Items con joins útiles para la plantilla
    items = cart.items.select_related("course_group", "course_group__course")
    return render(request, "academics/cart.html", {"cart": cart, "items": items, "term": term})

# ────────────────────────────────────────────────────────────────
# Agregar al carrito
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_student)
def cart_add(request, group_id: int):
    if CourseGroup is None:
        messages.error(request, "El modelo CourseGroup aún no está disponible.")
        return _redir("academics:academics_cart", "academics_cart")

    term = _current_term()
    if term is None:
        messages.error(request, "No hay término activo. Solicita a Secretaría que configure el período.")
        return _redir("academics:academics_cart", "academics_cart")

    group = get_object_or_404(CourseGroup, pk=group_id)
    try:
        add_to_cart(request.user, term, group)
        messages.success(request, "Reservado en carrito.")
    except Exception as e:
        messages.error(request, str(e))

    return _redir("academics:academics_cart", "academics_cart")

# ────────────────────────────────────────────────────────────────
# Quitar del carrito
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_student)
def cart_remove(request, group_id: int):
    if CourseGroup is None:
        messages.error(request, "El modelo CourseGroup aún no está disponible.")
        return _redir("academics:academics_cart", "academics_cart")

    term = _current_term()
    if term is None:
        messages.error(request, "No hay término activo.")
        return _redir("academics:academics_cart", "academics_cart")

    group = get_object_or_404(CourseGroup, pk=group_id)
    try:
        remove_from_cart(request.user, term, group)
        messages.success(request, "Quitado del carrito.")
    except Exception as e:
        messages.error(request, str(e))

    return _redir("academics:academics_cart", "academics_cart")

# ────────────────────────────────────────────────────────────────
# Confirmar matrícula (procesa carrito completo)
# ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_student)
def cart_confirm(request):
    term = _current_term()
    if term is None:
        messages.error(request, "No hay término activo.")
        return _redir("academics:academics_cart", "academics_cart")

    try:
        n = confirm_cart(request.user, term)
        messages.success(request, f"Matrícula confirmada: {n} secciones.")
    except Exception as e:
        messages.error(request, str(e))

    # Ajusta el destino si tienes vista de "mis matrículas"
    return _redir("academics:academics_cart", "academics_cart")
    # Ej.: return _redir("academics:academics_my_enrollments", "academics_my_enrollments")

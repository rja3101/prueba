# apps/academics/services_enrollment.py
from __future__ import annotations
from datetime import timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone


# ────────────────────────────────────────────────────────────────
# Carga segura de modelos (si no existen, quedan en None)
# ────────────────────────────────────────────────────────────────
def _gm(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

Term = _gm("academics", "Term")
TermRule = _gm("academics", "TermRule")
EnrollmentCart = _gm("academics", "EnrollmentCart")
CartItem = _gm("academics", "CartItem")
CapReservation = _gm("academics", "CapReservation")
Enrollment = _gm("academics", "Enrollment")
CourseGroup = _gm("academics", "CourseGroup")
StudentProfile = _gm("academics", "StudentProfile")
PaymentOrder = _gm("academics", "PaymentOrder")
EnrollmentAttempt = _gm("academics", "EnrollmentAttempt")


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
class EnrollmentError(RuntimeError):
    pass


def _require(model, name: str):
    if model is None:
        raise EnrollmentError(f"El modelo requerido '{name}' aún no está disponible.")
    return model


def _now():
    return timezone.now()


def _cart_hold_minutes_for_term(term) -> int:
    """
    Obtiene minutos de retención de carrito desde TermRule.cart_hold_minutes si existe,
    si no, usa 15 min por defecto.
    """
    if TermRule is None or term is None:
        return 15
    try:
        rule = TermRule.objects.filter(term=term).first()
        if rule and hasattr(rule, "cart_hold_minutes") and rule.cart_hold_minutes:
            return int(rule.cart_hold_minutes)
    except Exception:
        pass
    return 15


# ────────────────────────────────────────────────────────────────
# API pública
# ────────────────────────────────────────────────────────────────
def get_or_create_cart(user, term):
    """
    Devuelve o crea un carrito activo para el usuario/term.
    """
    _require(EnrollmentCart, "EnrollmentCart")
    # term puede ser None; permitimos carrito sin término para desarrollo
    defaults = {}
    # Algunos modelos tienen is_active; si no, lo ignoramos
    try:
        cart, created = EnrollmentCart.objects.get_or_create(
            student=user,
            term=term,
            defaults={**defaults, "is_active": True} if hasattr(EnrollmentCart, "is_active") else defaults,
        )
        # Si existe el campo is_active y está False, lo reactivamos
        if hasattr(cart, "is_active") and not cart.is_active:
            cart.is_active = True
            cart.save(update_fields=["is_active"])
        return cart
    except Exception as e:
        raise EnrollmentError(f"No se pudo obtener/crear el carrito: {e}")


@transaction.atomic
def add_to_cart(user, term, group):
    """
    Agrega un CourseGroup al carrito. Crea/renueva reserva de capacidad si ese modelo existe.
    """
    _require(CourseGroup, "CourseGroup")
    _require(EnrollmentCart, "EnrollmentCart")

    if group is None:
        raise EnrollmentError("Grupo inválido.")

    cart = get_or_create_cart(user, term)

    # Evitar duplicados: si ya existe CartItem para ese grupo
    if CartItem is not None:
        try:
            exists = CartItem.objects.filter(cart=cart, course_group=group).exists()
            if exists:
                # Renovamos reserva si aplica
                if CapReservation is not None:
                    _renew_capreservation(user, term, group)
                return cart
        except Exception as e:
            raise EnrollmentError(f"Error revisando ítem de carrito: {e}")

    # Crear CartItem
    if CartItem is not None:
        try:
            ci = CartItem(cart=cart, course_group=group)
            # reserved_until si el campo existe
            hold_minutes = _cart_hold_minutes_for_term(term)
            if hasattr(ci, "reserved_until"):
                ci.reserved_until = _now() + timedelta(minutes=hold_minutes)
            ci.save()
        except Exception as e:
            raise EnrollmentError(f"No se pudo agregar al carrito: {e}")
    # Crear/renovar reserva de capacidad (si el modelo existe)
    if CapReservation is not None:
        _renew_capreservation(user, term, group)

    return cart


def _renew_capreservation(user, term, group):
    """Crea o renueva la reserva de cupo si el modelo CapReservation existe."""
    if CapReservation is None:
        return
    try:
        hold_minutes = _cart_hold_minutes_for_term(term)
        expires = _now() + timedelta(minutes=hold_minutes)
        obj, created = CapReservation.objects.get_or_create(
            course_group=group,
            student=user,
            term=term,
            defaults={"reserved_until": expires} if _has_field(CapReservation, "reserved_until") else {},
        )
        if not created and _has_field(CapReservation, "reserved_until"):
            obj.reserved_until = expires
            obj.save(update_fields=["reserved_until"])
    except Exception:
        # No hacemos hard-fail por reservas; el carrito sigue
        pass


@transaction.atomic
def remove_from_cart(user, term, group):
    """
    Quita un grupo del carrito. Limpia reserva si el modelo existe.
    """
    _require(CourseGroup, "CourseGroup")
    _require(EnrollmentCart, "EnrollmentCart")

    cart = get_or_create_cart(user, term)

    if CartItem is not None:
        try:
            CartItem.objects.filter(cart=cart, course_group=group).delete()
        except Exception as e:
            raise EnrollmentError(f"No se pudo quitar del carrito: {e}")

    if CapReservation is not None:
        try:
            CapReservation.objects.filter(course_group=group, student=user, term=term).delete()
        except Exception:
            pass

    return cart


@transaction.atomic
def confirm_cart(user, term) -> int:
    """
    Convierte los items del carrito en Enrollment(s).
    Retorna la cantidad de secciones matriculadas.
    """
    _require(Enrollment, "Enrollment")
    _require(EnrollmentCart, "EnrollmentCart")
    _require(CourseGroup, "CourseGroup")

    cart = get_or_create_cart(user, term)

    # Obtener items (si el modelo existe)
    items_qs = []
    if CartItem is not None:
        try:
            items_qs = list(
                CartItem.objects.select_related("course_group").filter(cart=cart)
            )
        except Exception as e:
            raise EnrollmentError(f"No se pudo leer el carrito: {e}")

    if not items_qs:
        return 0

    created_count = 0
    for it in items_qs:
        group = getattr(it, "course_group", None)
        if group is None:
            continue
        try:
            # Enrollment: (student, group) o (student, course_group) según tu modelo
            kwargs = {}
            # intentamos ambos nombres habituales
            if _has_field(Enrollment, "group"):
                kwargs["group"] = group
            elif _has_field(Enrollment, "course_group"):
                kwargs["course_group"] = group
            else:
                raise EnrollmentError("El modelo Enrollment no tiene FK al grupo (group/course_group).")

            enr, created = Enrollment.objects.get_or_create(student=user, **kwargs)
            created_count += int(created)
        except Exception as e:
            # Registramos intento si existe el modelo
            _log_attempt(user, term, action=f"enroll:{getattr(group, 'id', None)}", error=str(e))
            # Continuamos con el resto (mejor experiencia)
            continue

    # Marcar carrito como inactivo / confirmado si existen esos campos
    try:
        updates = []
        if hasattr(cart, "is_active") and cart.is_active:
            cart.is_active = False
            updates.append("is_active")
        if hasattr(cart, "confirmed_at"):
            cart.confirmed_at = _now()
            updates.append("confirmed_at")
        if updates:
            cart.save(update_fields=updates)
    except Exception:
        pass

    # Limpiar reservas del usuario si existe CapReservation
    if CapReservation is not None:
        try:
            CapReservation.objects.filter(student=user, term=term).delete()
        except Exception:
            pass

    return created_count


# ────────────────────────────────────────────────────────────────
# Utilidades privadas
# ────────────────────────────────────────────────────────────────
def _has_field(Model, field_name: str) -> bool:
    if Model is None:
        return False
    try:
        return any(f.name == field_name for f in Model._meta.get_fields())
    except Exception:
        return False


def _log_attempt(user, term, action: str, error: str | None = None, payload=None, result=None):
    """Registra un intento de matrícula si existe el modelo EnrollmentAttempt."""
    if EnrollmentAttempt is None:
        return
    try:
        kwargs = {"student": user, "term": term, "action": action}
        if _has_field(EnrollmentAttempt, "payload"):
            kwargs["payload"] = payload
        if _has_field(EnrollmentAttempt, "result"):
            kwargs["result"] = {"error": error} if error else result
        EnrollmentAttempt.objects.create(**kwargs)
    except Exception:
        # logging opcional; no interrumpimos el flujo principal
        pass

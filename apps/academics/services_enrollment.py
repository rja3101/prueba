# Esqueleto mínimo; pega aquí tus reglas completas
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from .models import (Term, TermRule, EnrollmentCart, CartItem, CapReservation,
                     Enrollment, CourseGroup, StudentProfile, PaymentOrder, EnrollmentAttempt)

def get_or_create_cart(student, term): return EnrollmentCart.objects.get_or_create(student=student, term=term, defaults={"is_active":True})[0]

@transaction.atomic
def add_to_cart(student, term, group):
    # bloquear cupo + crear reserva + item
    now = timezone.now()
    hold = now + timedelta(minutes=term.rules.cart_hold_minutes)
    g = CourseGroup.objects.select_for_update().get(pk=group.pk)
    if g.available_slots <= 0: raise ValidationError("Sin cupo disponible.")
    cart = get_or_create_cart(student, term)
    CartItem.objects.get_or_create(cart=cart, course_group=g, defaults={"reserved_until": hold})
    CapReservation.objects.get_or_create(course_group=g, student=student, term=term, defaults={"reserved_until": hold})
    EnrollmentAttempt.objects.create(student=student, term=term, action="ADD_TO_CART", payload={"group": g.id})
    return cart

@transaction.atomic
def remove_from_cart(student, term, group):
    CartItem.objects.filter(cart__student=student, cart__term=term, course_group=group).delete()
    CapReservation.objects.filter(student=student, term=term, course_group=group).delete()
    EnrollmentAttempt.objects.create(student=student, term=term, action="REMOVE_FROM_CART", payload={"group": group.id})

@transaction.atomic
def confirm_cart(student, term):
    cart = EnrollmentCart.objects.select_for_update().get(student=student, term=term, is_active=True)
    items = list(cart.items.select_related("course_group"))
    now = timezone.now()
    valid = [it for it in items if it.reserved_until > now]
    if not valid: raise ValidationError("Tu carrito no tiene reservas válidas.")
    # revalidar cupo
    for it in valid:
        g = CourseGroup.objects.select_for_update().get(pk=it.course_group_id)
        if g.available_slots <= 0: raise ValidationError(f"Sin cupo en {g}.")
    created = 0
    for it in valid:
        Enrollment.objects.get_or_create(student=student, course_group=it.course_group)
        created += 1
        CapReservation.objects.filter(student=student, term=term, course_group=it.course_group).delete()
        it.delete()
    cart.is_active = False; cart.confirmed_at = now; cart.save()
    PaymentOrder.objects.create(student=student, term=term, amount=0)
    EnrollmentAttempt.objects.create(student=student, term=term, action="CONFIRM", result={"enrolled": created})
    return created

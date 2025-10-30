from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Term, CourseGroup
from .services_enrollment import add_to_cart, remove_from_cart, confirm_cart, get_or_create_cart
def is_student(u): return hasattr(u,"role") and u.role and u.role.name=="Alumno"

@login_required @user_passes_test(is_student)
def offerings(request):
    term = Term.objects.order_by("-start_date").first()
    groups = CourseGroup.objects.select_related("course","course__teacher").all().order_by("course__code","section")
    return render(request, "academics/offerings_cart.html", {"groups": groups, "term": term})

@login_required @user_passes_test(is_student)
def cart_view(request):
    term = Term.objects.order_by("-start_date").first()
    cart = get_or_create_cart(request.user, term)
    return render(request, "academics/cart.html", {"cart": cart, "items": cart.items.select_related("course_group","course_group__course")})

@login_required @user_passes_test(is_student)
def cart_add(request, group_id:int):
    term = Term.objects.order_by("-start_date").first()
    group = get_object_or_404(CourseGroup, pk=group_id)
    try: add_to_cart(request.user, term, group); messages.success(request, "Reservado en carrito.")
    except Exception as e: messages.error(request, str(e))
    return redirect("academics_cart")

@login_required @user_passes_test(is_student)
def cart_remove(request, group_id:int):
    term = Term.objects.order_by("-start_date").first()
    group = get_object_or_404(CourseGroup, pk=group_id)
    try: remove_from_cart(request.user, term, group); messages.success(request, "Quitado del carrito.")
    except Exception as e: messages.error(request, str(e))
    return redirect("academics_cart")

@login_required @user_passes_test(is_student)
def cart_confirm(request):
    term = Term.objects.order_by("-start_date").first()
    try: n = confirm_cart(request.user, term); messages.success(request, f"Matrícula confirmada: {n} secciones.")
    except Exception as e: messages.error(request, str(e))
    return redirect("academics_my_enrollments")

# apps/users/views.py
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.conf import settings


class RoleBasedLoginView(LoginView):
    template_name = "users/login.html"  # plantilla que haremos abajo

    def get_success_url(self):
        user = self.request.user


        # Según el rol:
        role_name = getattr(getattr(user, "role", None), "name", "").lower()

        if role_name == "alumno":
            return reverse_lazy("academics:student_dashboard")
        elif role_name == "docente":
            # Por ahora placeholder
            return reverse_lazy("academics:teacher_dashboard")  # para más adelante
        else:
            # default: lo mandas a home o algo neutro
            return reverse_lazy("home")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("users:login")

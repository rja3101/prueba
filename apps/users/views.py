# apps/users/views.py
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class RoleBasedLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True  # si ya está logueado, lo manda directo

    def get_success_url(self):
        user = self.request.user

        if not user.is_authenticated:
            return reverse_lazy("users:login")

        role = getattr(user, "role", None)
        role_name = getattr(role, "name", "") or ""
        role_name = role_name.lower()

        if role_name == "alumno":
            return reverse_lazy("academics:student_dashboard")
        if role_name == "docente":
            return reverse_lazy("academics:teacher_dashboard")

        return reverse_lazy("home")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("users:login")

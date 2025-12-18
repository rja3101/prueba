from django.urls import path
from .views import RoleBasedLoginView, CustomLogoutView

app_name = "users"

urlpatterns = [
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
]

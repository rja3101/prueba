from django.urls import path
from .views import users_index

urlpatterns = [
    path("", users_index, name="users_index"),
]

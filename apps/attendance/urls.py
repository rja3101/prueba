from django.urls import path
from .views import attendance_index

urlpatterns = [
    path("", attendance_index, name="attendance_index"),
]

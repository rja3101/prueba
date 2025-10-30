from django.urls import path
from . import views_teacher, views_checkin

app_name = "attendance"
urlpatterns = [
    path("teacher/today/", views_teacher.today_sessions, name="today"),
    path("teacher/checkin/<int:session_id>/", views_checkin.checkin_list, name="checkin"),
]

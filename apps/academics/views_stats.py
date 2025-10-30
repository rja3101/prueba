from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Min
from django.shortcuts import render, get_object_or_404
from .models import CourseGroup, Grade

@login_required
def group_stats_view(request, group_id:int):
    cg = get_object_or_404(CourseGroup.objects.select_related("course"), pk=group_id)
    stats = Grade.objects.filter(assessment__course_group=cg).aggregate(avg=Avg("score"), mx=Max("score"), mn=Min("score"))
    rows = (Grade.objects.filter(assessment__course_group=cg)
            .select_related("student","assessment")
            .order_by("student__username"))
    labels = [f"{g.student.username}-{g.assessment.title}" for g in rows]
    scores = [float(g.score) for g in rows]
    return render(request, "academics/group_stats.html", {"course_group": cg, "stats": stats, "labels": labels, "scores": scores})

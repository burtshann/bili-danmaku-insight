from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("csrf/", views.csrf_cookie, name="csrf"),
    path("analyses/", views.create_analysis, name="create-analysis"),
    path("analyses/history/", views.analysis_history, name="analysis-history"),
    path("analyses/<int:video_id>/", views.analysis_detail, name="analysis-detail"),
    path("tasks/<uuid:task_id>/", views.task_detail, name="task-detail"),
    path("exports/", views.create_export, name="create-export"),
    path("downloads/", views.create_download, name="create-download"),
]

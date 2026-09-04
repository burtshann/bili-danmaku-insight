from django.contrib import admin

from .models import AnalysisTask, DanmakuSummary, ExportRecord, Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "bvid", "owner_name", "updated_at")
    search_fields = ("title", "bvid", "owner_name")


@admin.register(AnalysisTask)
class AnalysisTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "progress", "created_at")
    list_filter = ("kind", "status")
    readonly_fields = ("created_at", "started_at", "completed_at")


admin.site.register(DanmakuSummary)
admin.site.register(ExportRecord)

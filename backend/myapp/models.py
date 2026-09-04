import uuid

from django.db import models


class Video(models.Model):
    bvid = models.CharField(max_length=20, unique=True, null=True, blank=True)
    source_url = models.URLField(max_length=500)
    title = models.CharField(max_length=300, blank=True)
    owner_name = models.CharField(max_length=120, blank=True)
    owner_id = models.CharField(max_length=32, blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or self.bvid or self.source_url

    def to_dict(self):
        return {
            "id": self.pk,
            "bvid": self.bvid,
            "url": self.source_url,
            "title": self.title,
            "owner_name": self.owner_name,
            "owner_id": self.owner_id,
            "cover_url": self.cover_url,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class AnalysisTask(models.Model):
    class Kind(models.TextChoices):
        ANALYSIS = "analysis", "Analysis"
        DOWNLOAD = "download", "Download"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    source_url = models.URLField(max_length=500)
    video = models.ForeignKey(Video, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    parameters = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    file_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.kind}:{self.id}:{self.status}"


class DanmakuSummary(models.Model):
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name="danmaku_summary")
    total_danmaku = models.PositiveIntegerField(default=0)
    top_words = models.JSONField(default=list)
    timeline = models.JSONField(default=list)
    peak_segments = models.JSONField(default=list)
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            "id": self.pk,
            "total_danmaku": self.total_danmaku,
            "top_words": self.top_words,
            "timeline": self.timeline,
            "peak_segments": self.peak_segments,
            "metrics": self.metrics,
            "updated_at": self.updated_at.isoformat(),
        }


class ExportRecord(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="exports")
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500)
    format = models.CharField(max_length=20, default="xlsx")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

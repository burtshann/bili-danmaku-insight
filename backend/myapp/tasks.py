import logging

from celery import shared_task
from django.db import close_old_connections
from django.utils import timezone

from .models import AnalysisTask, DanmakuSummary, Video
from .services.analysis import analyze_danmaku
from .services.bilibili import BilibiliClient, normalize_service_error
from .services.download import DownloadError, download_video
from .services.validation import extract_bvid

logger = logging.getLogger(__name__)


def update_progress(task_id, progress):
    AnalysisTask.objects.filter(pk=task_id).update(progress=max(0, min(99, int(progress))))


def save_video(metadata):
    defaults = {
        "source_url": metadata["source_url"],
        "title": metadata.get("title", ""),
        "owner_name": metadata.get("owner_name", ""),
        "owner_id": metadata.get("owner_id", ""),
        "cover_url": metadata.get("cover_url", ""),
        "duration_seconds": metadata.get("duration_seconds", 0),
        "metadata": metadata.get("metadata", {}),
    }
    video, _ = Video.objects.update_or_create(bvid=metadata["bvid"], defaults=defaults)
    return video


def run_analysis(task):
    update_progress(task.pk, 10)
    payload = BilibiliClient().fetch(task.source_url)
    update_progress(task.pk, 50)
    video = save_video(payload["metadata"])
    parameters = task.parameters or {}
    result = analyze_danmaku(
        payload["danmaku"],
        duration_seconds=video.duration_seconds,
        top_n=parameters.get("top_n", 20),
        bucket_seconds=parameters.get("bucket_seconds", 10),
        window_seconds=parameters.get("window_seconds", 3),
        peak_count=parameters.get("peak_count", 5),
    )
    summary, _ = DanmakuSummary.objects.update_or_create(
        video=video,
        defaults={
            "total_danmaku": result["total_danmaku"],
            "top_words": result["top_words"],
            "timeline": result["timeline"],
            "peak_segments": result["peak_segments"],
            "metrics": result["metrics"],
        },
    )
    task.video = video
    task.result = {"video": video.to_dict(), "analysis": summary.to_dict()}
    update_progress(task.pk, 95)


def run_download(task):
    bvid = extract_bvid(task.source_url)
    video = Video.objects.filter(bvid=bvid).first() if bvid else None
    result = download_video(task.source_url, lambda value: update_progress(task.pk, value))
    task.video = video
    task.file_url = result["file_url"]
    task.result = result


def execute_task(task_id):
    close_old_connections()
    try:
        task = AnalysisTask.objects.get(pk=task_id)
        task.status = AnalysisTask.Status.RUNNING
        task.progress = 1
        task.started_at = timezone.now()
        task.error_message = ""
        task.save(update_fields=["status", "progress", "started_at", "error_message"])

        if task.kind == AnalysisTask.Kind.ANALYSIS:
            run_analysis(task)
        elif task.kind == AnalysisTask.Kind.DOWNLOAD:
            run_download(task)
        else:
            raise ValueError(f"Unsupported task kind: {task.kind}")

        task.status = AnalysisTask.Status.SUCCESS
        task.progress = 100
        task.completed_at = timezone.now()
        task.save(
            update_fields=[
                "status",
                "progress",
                "video",
                "result",
                "file_url",
                "completed_at",
            ]
        )
        logger.info("task completed", extra={"task_id": task.pk, "video_id": task.video_id})
    except Exception as exc:
        message = normalize_service_error(exc)
        if isinstance(exc, DownloadError):
            message = str(exc)
        AnalysisTask.objects.filter(pk=task_id).update(
            status=AnalysisTask.Status.FAILED,
            error_message=message,
            completed_at=timezone.now(),
        )
        logger.exception("task failed", extra={"task_id": task_id})
    finally:
        close_old_connections()


@shared_task(name="myapp.execute_analysis_task")
def execute_task_celery(task_id):
    execute_task(task_id)

import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import AnalysisTask, DanmakuSummary, Video
from .rate_limit import rate_limit
from .services.export import create_excel_export
from .services.validation import (
    InputValidationError,
    parse_bounded_int,
    validate_bilibili_url,
)
from .task_queue import submit_task


def parse_json_body(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputValidationError("请求体必须是有效的 JSON") from exc
    if not isinstance(body, dict):
        raise InputValidationError("请求体必须是 JSON 对象")
    return body


def task_payload(task):
    return {
        "id": str(task.pk),
        "kind": task.kind,
        "status": task.status,
        "progress": task.progress,
        "source_url": task.source_url,
        "video_id": task.video_id,
        "result": task.result if task.status == AnalysisTask.Status.SUCCESS else {},
        "file_url": task.file_url,
        "error": task.error_message if task.status == AnalysisTask.Status.FAILED else "",
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def create_task(kind, source_url, parameters=None):
    task = AnalysisTask.objects.create(
        kind=kind,
        source_url=source_url,
        parameters=parameters or {},
    )
    try:
        submit_task(task.pk)
    except Exception as exc:
        task.status = AnalysisTask.Status.FAILED
        task.error_message = "任务队列暂时不可用，请稍后重试"
        task.save(update_fields=["status", "error_message"])
        raise RuntimeError("任务队列暂时不可用，请稍后重试") from exc
    task.refresh_from_db()
    return task


@require_GET
def index(request):
    return JsonResponse(
        {
            "name": "Bili Danmaku Insight API",
            "version": "1.0",
            "health": "/api/v1/health/",
        }
    )


@require_GET
def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "task_execution_mode": settings.TASK_EXECUTION_MODE,
        }
    )


@require_GET
@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({"detail": "CSRF cookie initialized."})


@require_POST
@rate_limit("analysis", "ANALYSIS_RATE_LIMIT")
def create_analysis(request):
    try:
        body = parse_json_body(request)
        source_url = validate_bilibili_url(body.get("url", ""))
        parameters = {
            "top_n": parse_bounded_int(body.get("top_n"), "top_n", 20, 5, 50),
            "bucket_seconds": parse_bounded_int(
                body.get("bucket_seconds"), "bucket_seconds", 10, 5, 60
            ),
            "window_seconds": parse_bounded_int(
                body.get("window_seconds"), "window_seconds", 3, 1, 15
            ),
            "peak_count": parse_bounded_int(
                body.get("peak_count"), "peak_count", 5, 1, 10
            ),
        }
        task = create_task(AnalysisTask.Kind.ANALYSIS, source_url, parameters)
        return JsonResponse({"task": task_payload(task)}, status=202)
    except InputValidationError as exc:
        return JsonResponse({"error": str(exc), "code": "invalid_request"}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc), "code": "queue_unavailable"}, status=503)


@require_POST
@rate_limit("download", "DOWNLOAD_RATE_LIMIT")
def create_download(request):
    try:
        body = parse_json_body(request)
        source_url = validate_bilibili_url(body.get("url", ""))
        task = create_task(AnalysisTask.Kind.DOWNLOAD, source_url)
        return JsonResponse({"task": task_payload(task)}, status=202)
    except InputValidationError as exc:
        return JsonResponse({"error": str(exc), "code": "invalid_request"}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc), "code": "queue_unavailable"}, status=503)


@require_GET
def task_detail(request, task_id):
    task = get_object_or_404(AnalysisTask, pk=task_id)
    return JsonResponse({"task": task_payload(task)})


@require_GET
def analysis_history(request):
    try:
        limit = parse_bounded_int(request.GET.get("limit"), "limit", 12, 1, 50)
    except InputValidationError as exc:
        return JsonResponse({"error": str(exc), "code": "invalid_request"}, status=400)

    summaries = DanmakuSummary.objects.select_related("video").order_by("-updated_at")[:limit]
    items = [
        {
            "video": summary.video.to_dict(),
            "analysis": summary.to_dict(),
        }
        for summary in summaries
    ]
    return JsonResponse({"items": items, "count": len(items)})


@require_GET
def analysis_detail(request, video_id):
    video = get_object_or_404(Video, pk=video_id)
    summary = get_object_or_404(DanmakuSummary, video=video)
    return JsonResponse({"video": video.to_dict(), "analysis": summary.to_dict()})


@require_POST
@rate_limit("export", "ANALYSIS_RATE_LIMIT")
def create_export(request):
    try:
        body = parse_json_body(request)
        video_id = parse_bounded_int(body.get("video_id"), "video_id", None, 1, 2_147_483_647)
        if video_id is None:
            raise InputValidationError("video_id 不能为空")
        video = get_object_or_404(Video, pk=video_id)
        summary = get_object_or_404(DanmakuSummary, video=video)
        export = create_excel_export(video, summary)
        return JsonResponse({"export": export}, status=201)
    except InputValidationError as exc:
        return JsonResponse({"error": str(exc), "code": "invalid_request"}, status=400)

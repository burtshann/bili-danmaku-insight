import threading
from pathlib import Path

import yt_dlp
from django.conf import settings

from .bilibili import HEADERS
from .validation import extract_bvid, validate_bilibili_url


class DownloadError(RuntimeError):
    pass


def maybe_start_waiting_game():
    if not settings.ENABLE_WAITING_GAME:
        return

    def run():
        try:
            from .waiting_game import run_waiting_game

            run_waiting_game()
        except Exception:
            return

    threading.Thread(target=run, daemon=True).start()


def download_video(raw_url, progress_callback=None):
    video_url = validate_bilibili_url(raw_url)
    identity = extract_bvid(video_url) or "bilibili_video"
    output_dir = Path(settings.DOWNLOAD_ROOT)
    output_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.MAX_VIDEO_DOWNLOAD_MB * 1024 * 1024

    for existing in output_dir.glob(f"{identity}.*"):
        if existing.is_file():
            existing.unlink()

    def progress_hook(payload):
        if not progress_callback:
            return
        status = payload.get("status")
        if status == "finished":
            progress_callback(95)
            return
        downloaded = payload.get("downloaded_bytes") or 0
        total = payload.get("total_bytes") or payload.get("total_bytes_estimate") or 0
        if total:
            progress_callback(min(90, max(5, int(downloaded / total * 90))))

    options = {
        "http_headers": HEADERS,
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": str(output_dir / f"{identity}.%(ext)s"),
        "merge_output_format": "mp4",
        "max_filesize": max_bytes,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
    }
    cookie_path = Path(settings.BASE_DIR) / "cookie" / "cookie.txt"
    if cookie_path.exists():
        options["cookiefile"] = str(cookie_path)

    maybe_start_waiting_game()
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([video_url])
    except Exception as exc:
        raise DownloadError(f"视频下载失败: {exc}") from exc

    candidates = sorted(
        (path for path in output_dir.glob(f"{identity}.*") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise DownloadError("下载完成后未找到输出文件")
    output_file = candidates[0]
    if output_file.stat().st_size > max_bytes:
        output_file.unlink(missing_ok=True)
        raise DownloadError(f"视频超过 {settings.MAX_VIDEO_DOWNLOAD_MB} MB 限制")

    return {
        "file_name": output_file.name,
        "file_url": settings.DOWNLOAD_URL + output_file.name,
    }

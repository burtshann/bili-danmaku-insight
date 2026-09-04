import re
from urllib.parse import urlsplit, urlunsplit

VIDEO_HOSTS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com"}
SHORT_LINK_HOSTS = {"b23.tv", "www.b23.tv"}
BVID_PATTERN = re.compile(r"BV[0-9A-Za-z]{10}")


class InputValidationError(ValueError):
    pass


def extract_bvid(value):
    match = BVID_PATTERN.search(value or "")
    return match.group(0) if match else ""


def validate_bilibili_url(value, require_video_path=True):
    raw_value = (value or "").strip()
    if BVID_PATTERN.fullmatch(raw_value):
        raw_value = f"https://www.bilibili.com/video/{raw_value}"

    if not raw_value:
        raise InputValidationError("视频链接不能为空")
    if len(raw_value) > 500:
        raise InputValidationError("视频链接过长")

    parsed = urlsplit(raw_value)
    if parsed.scheme not in {"http", "https"}:
        raise InputValidationError("仅支持 HTTP 或 HTTPS 链接")
    if parsed.username or parsed.password:
        raise InputValidationError("视频链接不能包含账号信息")

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if hostname not in VIDEO_HOSTS | SHORT_LINK_HOSTS:
        raise InputValidationError("仅支持 bilibili.com 或 b23.tv 视频链接")

    try:
        port = parsed.port
    except ValueError as exc:
        raise InputValidationError("视频链接端口无效") from exc
    if port not in {None, 80, 443}:
        raise InputValidationError("视频链接不能使用自定义端口")

    if require_video_path and hostname in VIDEO_HOSTS:
        if not parsed.path.startswith("/video/") or not extract_bvid(parsed.path):
            raise InputValidationError("链接中未找到有效的 BV 号")

    clean_path = parsed.path or "/"
    return urlunsplit((parsed.scheme, parsed.netloc, clean_path, parsed.query, ""))


def parse_bounded_int(value, name, default, minimum, maximum):
    if value in {None, ""}:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name}必须是整数") from exc
    if not minimum <= parsed <= maximum:
        raise InputValidationError(f"{name}必须在 {minimum} 到 {maximum} 之间")
    return parsed

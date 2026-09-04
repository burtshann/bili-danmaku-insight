import hashlib
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def _client_identifier(request):
    if settings.TRUST_PROXY_HEADERS:
        real_ip = request.META.get("HTTP_X_REAL_IP", "").strip()
        if real_ip:
            return real_ip
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(bucket, setting_name, window_seconds=60):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            limit = max(1, int(getattr(settings, setting_name)))
            identity = hashlib.sha256(_client_identifier(request).encode()).hexdigest()[:20]
            key = f"rate-limit:{bucket}:{identity}"
            if cache.add(key, 1, timeout=window_seconds):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window_seconds)
                    count = 1

            if count > limit:
                response = JsonResponse(
                    {"error": "请求过于频繁，请稍后再试。", "code": "rate_limited"},
                    status=429,
                )
                response["Retry-After"] = str(window_seconds)
                return response
            return view(request, *args, **kwargs)

        return wrapped

    return decorator

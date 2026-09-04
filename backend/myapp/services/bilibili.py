import hashlib
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .validation import InputValidationError, extract_bvid, validate_bilibili_url

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


class BilibiliRequestError(RuntimeError):
    pass


def read_response_limited(response, max_bytes, label):
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                response.close()
                raise BilibiliRequestError(f"{label}超过允许的大小")
        except ValueError:
            pass

    body = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        body.extend(chunk)
        if len(body) > max_bytes:
            response.close()
            raise BilibiliRequestError(f"{label}超过允许的大小")

    response._content = bytes(body)
    response._content_consumed = True
    return response


def build_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def parse_initial_state(html):
    soup = BeautifulSoup(html, "html.parser")
    marker = "window.__INITIAL_STATE__"
    decoder = json.JSONDecoder()
    for script in soup.find_all("script"):
        source = script.string or script.get_text() or ""
        marker_index = source.find(marker)
        if marker_index < 0:
            continue
        equals_index = source.find("=", marker_index + len(marker))
        if equals_index < 0:
            continue
        try:
            payload, _ = decoder.raw_decode(source[equals_index + 1 :].lstrip())
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    return {}


def parse_danmaku_xml(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise BilibiliRequestError(f"弹幕 XML 解析失败: {exc}") from exc

    items = []
    for element in root.findall(".//d"):
        text = (element.text or "").strip()
        if not text:
            continue
        try:
            timestamp = float(element.attrib.get("p", "0").split(",", 1)[0])
        except (TypeError, ValueError):
            continue
        items.append((timestamp, text))
    if not items:
        raise BilibiliRequestError("未获取到可分析的弹幕数据")
    return items


def extract_cid(state, html):
    candidates = [
        state.get("videoData", {}).get("cid"),
        state.get("epInfo", {}).get("cid"),
        state.get("cid"),
    ]
    for candidate in candidates:
        if str(candidate or "").isdigit():
            return str(candidate)
    match = re.search(r'"cid"\s*:\s*(\d+)', html)
    if match:
        return match.group(1)
    raise BilibiliRequestError("页面中未找到视频 CID，页面结构可能已经变化")


def extract_metadata(state, html, final_url):
    video_data = state.get("videoData") or state.get("epInfo") or {}
    owner = video_data.get("owner") or state.get("upData") or {}
    stats = video_data.get("stat") or {}
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = video_data.get("title") or (title_tag.get_text(strip=True) if title_tag else "")
    title = re.sub(r"[_-]哔哩哔哩.*$", "", title).strip()

    bvid = video_data.get("bvid") or extract_bvid(final_url) or extract_bvid(html)
    if not bvid:
        raise BilibiliRequestError("页面中未找到有效的 BV 号")

    return {
        "bvid": bvid,
        "source_url": f"https://www.bilibili.com/video/{bvid}",
        "title": title or bvid,
        "owner_name": str(owner.get("name") or ""),
        "owner_id": str(owner.get("mid") or ""),
        "cover_url": str(video_data.get("pic") or ""),
        "duration_seconds": int(video_data.get("duration") or 0),
        "metadata": {
            "aid": video_data.get("aid"),
            "views": stats.get("view"),
            "likes": stats.get("like"),
            "coins": stats.get("coin"),
            "favorites": stats.get("favorite"),
            "shares": stats.get("share"),
            "historical_danmaku": stats.get("danmaku"),
            "published_at": video_data.get("pubdate"),
            "description": video_data.get("desc") or "",
        },
    }


class BilibiliClient:
    def __init__(self, session=None):
        self.session = session or build_session()
        self.verify_ssl = settings.REQUEST_VERIFY_SSL

    def fetch_page(self, raw_url):
        current_url = validate_bilibili_url(raw_url)
        for _ in range(4):
            try:
                response = self.session.get(
                    current_url,
                    timeout=(5, 20),
                    verify=self.verify_ssl,
                    allow_redirects=False,
                    stream=True,
                )
            except requests.RequestException as exc:
                raise BilibiliRequestError(f"Bilibili 页面请求失败: {exc}") from exc

            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise BilibiliRequestError("Bilibili 返回了无目标地址的重定向")
                response.close()
                current_url = validate_bilibili_url(
                    urljoin(current_url, location),
                    require_video_path=False,
                )
                continue

            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise BilibiliRequestError(f"Bilibili 页面返回异常状态: {exc}") from exc
            validate_bilibili_url(response.url, require_video_path=False)
            read_response_limited(
                response,
                settings.MAX_BILIBILI_PAGE_MB * 1024 * 1024,
                "Bilibili 页面",
            )
            response.encoding = response.apparent_encoding or "utf-8"
            return response
        raise BilibiliRequestError("Bilibili 链接重定向次数过多")

    def fetch(self, raw_url):
        normalized_url = validate_bilibili_url(raw_url)
        cache_key = "bili-analysis:" + hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
        cached = cache.get(cache_key)
        if cached:
            cached["danmaku"] = [tuple(item) for item in cached["danmaku"]]
            return cached

        page_response = self.fetch_page(normalized_url)
        state = parse_initial_state(page_response.text)
        cid = extract_cid(state, page_response.text)
        metadata = extract_metadata(state, page_response.text, page_response.url)

        danmaku_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
        try:
            danmaku_response = self.session.get(
                danmaku_url,
                timeout=(5, 20),
                verify=self.verify_ssl,
                stream=True,
            )
            danmaku_response.raise_for_status()
            read_response_limited(
                danmaku_response,
                settings.MAX_DANMAKU_RESPONSE_MB * 1024 * 1024,
                "弹幕响应",
            )
            danmaku_response.encoding = "utf-8"
        except requests.RequestException as exc:
            raise BilibiliRequestError(f"弹幕接口请求失败: {exc}") from exc

        payload = {
            "metadata": metadata,
            "danmaku": parse_danmaku_xml(danmaku_response.text),
        }
        cache.set(cache_key, payload, timeout=settings.BILIBILI_CACHE_TTL)
        return payload


def normalize_service_error(exc):
    if isinstance(exc, (BilibiliRequestError, InputValidationError)):
        return str(exc)
    return "视频数据处理失败"

# 视频分析应用视图
import json
import os
import random
import re
import threading
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import jieba
import pygame
import requests
import yt_dlp as ydl
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from openpyxl import Workbook


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

VERIFY_SSL = os.environ.get("REQUEST_VERIFY_SSL", "true").lower() == "true"
DOWNLOAD_DIR = Path(settings.DOWNLOAD_ROOT)
COOKIE_FILE = Path(settings.BASE_DIR) / "cookie" / "cookie.txt"


def index(request):
    """Django 模板备用首页，主要演示界面由 React 前端提供。"""
    return render(request, "index.html")


def parse_request_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("无效的JSON数据") from exc


def extract_cid(html_content):
    match = re.search(r'"cid"\s*:\s*(\d+)', html_content)
    if not match:
        raise ValueError("无法提取有效的cid")
    return match.group(1)


def fetch_danmaku_data(video_url):
    """抓取 Bilibili 视频弹幕，返回 (出现时间, 弹幕文本) 列表。"""
    try:
        response = requests.get(
            video_url,
            headers=HEADERS,
            timeout=15,
            verify=VERIFY_SSL,
        )
        response.raise_for_status()
        response.encoding = "utf-8"

        cid = extract_cid(response.text)
        danmaku_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
        danmaku_response = requests.get(
            danmaku_url,
            headers=HEADERS,
            timeout=15,
            verify=VERIFY_SSL,
        )
        danmaku_response.raise_for_status()
        danmaku_response.encoding = "utf-8"

        root = ET.fromstring(danmaku_response.text)
        danmaku_list = []
        for item in root.findall(".//d"):
            text = (item.text or "").strip()
            if not text:
                continue
            try:
                timestamp = float(item.attrib.get("p", "0").split(",")[0])
            except ValueError:
                continue
            danmaku_list.append((timestamp, text))

        if not danmaku_list:
            raise ValueError("未获取到弹幕数据")
        return danmaku_list
    except ET.ParseError as exc:
        raise ValueError(f"解析XML数据时出错: {exc}") from exc
    except requests.RequestException as exc:
        raise ValueError(f"网络请求失败: {exc}") from exc


def process_text(danmaku_list):
    """清洗中文弹幕并统计最高频的五个词。"""
    all_text = " ".join(text for _, text in danmaku_list)
    cleaned_text = re.sub(r"[^\u4e00-\u9fa5]", "", all_text)
    words = [word for word in jieba.cut(cleaned_text) if len(word.strip()) >= 2]
    most_common_words = Counter(words).most_common(5)

    return {
        "words": [word for word, _ in most_common_words],
        "counts": [count for _, count in most_common_words],
    }


def calculate_max_danmaku(danmaku_times, window_size=3):
    """计算弹幕最密集的连续时间窗口。"""
    if not danmaku_times:
        return 0, 0, 0

    rounded_times = [round(float(time)) for time in danmaku_times]
    time_counts = Counter(rounded_times)
    start_time = min(time_counts)
    max_count = 0

    for time in time_counts:
        window_count = sum(time_counts.get(time + offset, 0) for offset in range(window_size))
        if window_count > max_count:
            max_count = window_count
            start_time = time

    return start_time, start_time + window_size, max_count


@csrf_exempt
def get_high_freq_data(request):
    """获取高频词数据 API。"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持POST请求"}, status=405)

    try:
        body = parse_request_body(request)
        video_url = body.get("danmaku")
        if not video_url:
            return JsonResponse({"error": "URL不能为空"}, status=400)

        danmaku_list = fetch_danmaku_data(video_url)
        return JsonResponse(process_text(danmaku_list))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
def get_max_danmaku(request):
    """获取弹幕峰值对应的精彩时间段 API。"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持POST请求"}, status=405)

    try:
        body = parse_request_body(request)
        video_url = body.get("danmaku")
        if not video_url:
            return JsonResponse({"error": "URL不能为空"}, status=400)

        danmaku_list = fetch_danmaku_data(video_url)
        start_time, end_time, count = calculate_max_danmaku([time for time, _ in danmaku_list])
        return JsonResponse(
            {
                "start_time": start_time,
                "end_time": end_time,
                "count": count,
            }
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


def clear_previous_downloads():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for pattern in ("downloaded_video.*", "output.xlsx"):
        for file_path in DOWNLOAD_DIR.glob(pattern):
            if file_path.is_file():
                file_path.unlink()


def run_pygame_game():
    """运行等待小游戏。无图形环境时失败不会影响下载接口。"""
    try:
        pygame.init()
        screen_width = 800
        screen_height = 500
        screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("DLW Game")

        white = (255, 255, 255)
        black = (0, 0, 0)
        red = (255, 0, 0)

        class Player:
            def __init__(self):
                self.x = 50
                self.y = 150
                self.width = 20
                self.height = 20
                self.dy = 0
                self.gravity = 0.6
                self.jump_power = -10
                self.grounded = False

            def jump(self):
                if self.grounded:
                    self.dy = self.jump_power
                    self.grounded = False

            def update(self):
                self.y += self.dy
                if self.y + self.height < screen_height:
                    self.dy += self.gravity
                else:
                    self.y = screen_height - self.height
                    self.dy = 0
                    self.grounded = True

            def draw(self):
                pygame.draw.rect(screen, black, (self.x, self.y, self.width, self.height))

        class Obstacle:
            def __init__(self):
                self.x = screen_width
                self.y = screen_height - random.randint(20, 60)
                self.width = 20
                self.height = random.randint(20, 40)

            def update(self):
                self.x -= game_speed

            def draw(self):
                pygame.draw.rect(screen, red, (self.x, self.y, self.width, self.height))

        player = Player()
        obstacles = []
        game_speed = 5
        score = 0
        clock = pygame.time.Clock()
        game_over = False
        replay_button = pygame.Rect(screen_width // 2 - 100, screen_height // 2 - 50, 200, 100)

        try:
            font = pygame.font.Font("msyh.ttc", 48)
        except OSError:
            font = pygame.font.Font(None, 48)

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if game_over and replay_button.collidepoint(*event.pos):
                        game_over = False
                        player = Player()
                        obstacles = []
                        score = 0
                    elif not game_over:
                        player.jump()

            if not game_over:
                player.update()
                if random.random() < 0.01:
                    obstacles.append(Obstacle())

                for obstacle in list(obstacles):
                    obstacle.update()
                    if obstacle.x + obstacle.width < 0:
                        obstacles.remove(obstacle)
                        score += 1

                    hit_player = (
                        player.x < obstacle.x + obstacle.width
                        and player.x + player.width > obstacle.x
                        and player.y < obstacle.y + obstacle.height
                        and player.y + player.height > obstacle.y
                    )
                    if hit_player:
                        game_over = True

                screen.fill(white)
                player.draw()
                for obstacle in obstacles:
                    obstacle.draw()
                score_text = font.render(f"Score: {score}", True, black)
                screen.blit(score_text, (10, 10))
                pygame.display.flip()

            if game_over:
                screen.fill(white)
                text = font.render("Replay?", True, black)
                pygame.draw.rect(screen, red, replay_button)
                screen.blit(
                    text,
                    (
                        screen_width // 2 - text.get_width() // 2,
                        screen_height // 2 - text.get_height() // 2,
                    ),
                )
                pygame.display.flip()

            clock.tick(30)
        pygame.quit()
    except Exception as exc:
        print(f"等待小游戏启动失败: {exc}")


@csrf_exempt
def download_video(request):
    """下载视频 API。"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持POST请求"}, status=405)

    try:
        body = parse_request_body(request)
        video_url = body.get("url")
        if not video_url:
            return JsonResponse({"error": "URL不能为空"}, status=400)

        clear_previous_downloads()
        ydl_opts = {
            "http_headers": HEADERS,
            "format": "bestvideo[height<=720]+bestaudio/best",
            "outtmpl": str(DOWNLOAD_DIR / "downloaded_video.%(ext)s"),
            "merge_output_format": "mp4",
            "verbose": False,
        }
        if COOKIE_FILE.exists():
            ydl_opts["cookiefile"] = str(COOKIE_FILE)

        if os.environ.get("ENABLE_WAITING_GAME", "true").lower() == "true":
            threading.Thread(target=run_pygame_game, daemon=True).start()

        with ydl.YoutubeDL(ydl_opts) as downloader:
            downloader.download([video_url])

        return JsonResponse(
            {
                "message": "视频下载完成！",
                "file": settings.DOWNLOAD_URL + "downloaded_video.mp4",
            }
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"error": f"视频下载失败: {exc}"}, status=500)


def write_error_log(message):
    with open("video_errorlist.txt", "a", encoding="utf-8") as file:
        file.write(message + "\n")


def find_required_match(pattern, text, error_message):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(error_message)
    return match


@csrf_exempt
def download_excel(request):
    """抓取视频元数据并导出 Excel。"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持POST请求"}, status=405)

    try:
        body = parse_request_body(request)
        video_url = body.get("url")
        if not video_url:
            return JsonResponse({"error": "URL不能为空"}, status=400)

        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = requests.get(
            url=video_url,
            headers=HEADERS,
            timeout=15,
            verify=VERIFY_SSL,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        initial_state_script = soup.find(string=re.compile("window.__INITIAL_STATE__"))
        if not initial_state_script:
            raise ValueError("未找到视频初始化数据")
        initial_state_text = initial_state_script.string or ""

        author_id = find_required_match(r'"mid":(\d+)', initial_state_text, "未找到UP主ID").group(1)
        video_aid = find_required_match(r'"aid":(\d+)', initial_state_text, "未找到视频aid").group(1)
        duration_match = find_required_match(
            r'"duration":(\d+)',
            initial_state_text,
            "未找到视频时长",
        )
        video_duration = max(int(duration_match.group(1)) - 2, 0)

        title_tag = soup.find("title")
        title = re.sub(r"_哔哩哔哩_bilibili", "", title_tag.text if title_tag else "").strip()
        if not title:
            title = "未找到标题"

        keywords_tag = soup.find("meta", itemprop="keywords")
        keywords_content = keywords_tag["content"] if keywords_tag and keywords_tag.has_attr("content") else ""
        keywords_list = keywords_content.replace(title + ",", "").split(",") if keywords_content else []
        tags = ",".join(keywords_list[:-4]) if len(keywords_list) > 4 else ",".join(keywords_list)

        description_tag = soup.find("meta", itemprop="description")
        meta_description = (
            description_tag["content"] if description_tag and description_tag.has_attr("content") else ""
        )
        numbers = re.findall(
            r"[\s\S]*?视频播放量 (\d+)、弹幕量 (\d+)、点赞数 (\d+)、投硬币枚数 (\d+)、收藏人数 (\d+)、转发人数 (\d+)",
            meta_description,
        )
        if not numbers:
            return JsonResponse({"error": "Excel未找到相关数据，可能为分集视频"}, status=400)

        author_search = re.search(r"视频作者\s*([^,]+)", meta_description)
        author = author_search.group(1).strip() if author_search else "未找到作者"

        author_desc_match = re.search(r"作者简介 (.+?),", meta_description)
        author_desc = author_desc_match.group(1) if author_desc_match else "未找到作者简介"

        video_desc = re.split(r",\s*", meta_description)[0].strip() if meta_description else "未找到视频简介"
        upload_date_tag = soup.find("meta", itemprop="uploadDate")
        publish_date = (
            upload_date_tag["content"]
            if upload_date_tag and upload_date_tag.has_attr("content")
            else "未找到发布时间"
        )

        views, danmaku, likes, coins, favorites, shares = [int(value) for value in numbers[0]]
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "bilibili_video"
        worksheet.append(
            [
                "标题",
                "链接",
                "up主",
                "up主id",
                "精确播放数",
                "历史累计弹幕数",
                "点赞数",
                "投硬币枚数",
                "收藏人数",
                "转发人数",
                "发布时间",
                "视频时长(秒)",
                "视频简介",
                "作者简介",
                "标签",
                "视频aid",
            ]
        )
        worksheet.append(
            [
                title,
                video_url,
                author,
                author_id,
                views,
                danmaku,
                likes,
                coins,
                favorites,
                shares,
                publish_date,
                video_duration,
                video_desc,
                author_desc,
                tags,
                video_aid,
            ]
        )
        output_file = DOWNLOAD_DIR / "output.xlsx"
        workbook.save(output_file)

        return JsonResponse(
            {
                "message": "Excel下载完成！",
                "file": settings.DOWNLOAD_URL + "output.xlsx",
            }
        )
    except ValueError as exc:
        write_error_log(f"视频发生错误: {exc}")
        return JsonResponse({"error": str(exc)}, status=400)
    except requests.RequestException as exc:
        write_error_log(f"视频发生错误: {exc}")
        return JsonResponse({"error": f"网络请求失败: {exc}"}, status=400)
    except Exception as exc:
        write_error_log(f"视频发生错误: {exc}")
        return JsonResponse({"error": "无效的 URL！"}, status=400)

import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import jieba

STOPWORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "stopwords_zh.txt"


@lru_cache(maxsize=1)
def load_stopwords():
    if not STOPWORDS_FILE.exists():
        return set()
    return {
        line.strip()
        for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def extract_top_words(danmaku_list, top_n=20):
    text = " ".join(content for _, content in danmaku_list)
    chinese_text = " ".join(re.findall(r"[\u4e00-\u9fff]+", text))
    stopwords = load_stopwords()
    words = [
        word.strip()
        for word in jieba.cut(chinese_text)
        if len(word.strip()) >= 2 and word.strip() not in stopwords
    ]
    return [
        {"word": word, "count": count}
        for word, count in Counter(words).most_common(top_n)
    ]


def build_timeline(danmaku_list, bucket_seconds=10, duration_seconds=0):
    counts = Counter(int(timestamp // bucket_seconds) for timestamp, _ in danmaku_list)
    observed_duration = max((timestamp for timestamp, _ in danmaku_list), default=0)
    duration = max(float(duration_seconds or 0), observed_duration)
    highest_observed_bucket = max(counts, default=-1) + 1
    bucket_count = max(1, math.ceil(duration / bucket_seconds), highest_observed_bucket)
    return [
        {
            "start": index * bucket_seconds,
            "end": (index + 1) * bucket_seconds,
            "count": counts.get(index, 0),
        }
        for index in range(bucket_count)
    ]


def find_peak_segments(danmaku_times, window_seconds=3, limit=5):
    times = sorted(max(0.0, float(value)) for value in danmaku_times)
    if not times:
        return []

    candidates = []
    right = 0
    for left, start in enumerate(times):
        right = max(right, left)
        while right < len(times) and times[right] < start + window_seconds:
            right += 1
        candidates.append(
            {
                "start": round(start, 2),
                "end": round(start + window_seconds, 2),
                "count": right - left,
            }
        )

    selected = []
    for candidate in sorted(candidates, key=lambda item: (-item["count"], item["start"])):
        overlaps = any(
            candidate["start"] < existing["end"] and candidate["end"] > existing["start"]
            for existing in selected
        )
        if not overlaps:
            selected.append(candidate)
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda item: (-item["count"], item["start"]))


def analyze_danmaku(
    danmaku_list,
    duration_seconds=0,
    top_n=20,
    bucket_seconds=10,
    window_seconds=3,
    peak_count=5,
):
    timeline = build_timeline(danmaku_list, bucket_seconds, duration_seconds)
    peaks = find_peak_segments(
        [timestamp for timestamp, _ in danmaku_list],
        window_seconds,
        peak_count,
    )
    observed_duration = max((timestamp for timestamp, _ in danmaku_list), default=0)
    effective_duration = max(float(duration_seconds or 0), observed_duration, 1)
    total = len(danmaku_list)
    peak_value = peaks[0]["count"] if peaks else 0
    return {
        "total_danmaku": total,
        "top_words": extract_top_words(danmaku_list, top_n),
        "timeline": timeline,
        "peak_segments": peaks,
        "metrics": {
            "average_per_minute": round(total / effective_duration * 60, 2),
            "peak_per_second": round(peak_value / window_seconds, 2),
            "bucket_seconds": bucket_seconds,
            "window_seconds": window_seconds,
        },
    }


def process_text(danmaku_list):
    words = extract_top_words(danmaku_list, top_n=5)
    return {
        "words": [item["word"] for item in words],
        "counts": [item["count"] for item in words],
    }


def calculate_max_danmaku(danmaku_times, window_size=3):
    peaks = find_peak_segments(danmaku_times, window_size, limit=1)
    if not peaks:
        return 0, 0, 0
    peak = peaks[0]
    return peak["start"], peak["end"], peak["count"]

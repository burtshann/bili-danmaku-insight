from django.test import SimpleTestCase

from myapp.services.analysis import (
    analyze_danmaku,
    build_timeline,
    calculate_max_danmaku,
    find_peak_segments,
)


class DanmakuAnalysisTests(SimpleTestCase):
    def setUp(self):
        self.items = [
            (2.1, "这个视频真的很好看"),
            (2.4, "视频内容很好看"),
            (3.1, "这个内容值得收藏"),
            (6.0, "后面的内容也很好看"),
            (6.2, "后面的内容也很好看"),
        ]

    def test_exact_sliding_window_keeps_subsecond_precision(self):
        start, end, count = calculate_max_danmaku(
            [timestamp for timestamp, _ in self.items]
        )
        self.assertEqual((start, end, count), (2.1, 5.1, 3))

    def test_peak_segments_do_not_overlap(self):
        peaks = find_peak_segments(
            [1.0, 1.2, 1.4, 5.0, 5.1, 9.0],
            window_seconds=2,
            limit=3,
        )
        self.assertEqual([item["count"] for item in peaks], [3, 2, 1])
        for index, current in enumerate(peaks):
            for other in peaks[index + 1 :]:
                self.assertTrue(
                    current["end"] <= other["start"]
                    or other["end"] <= current["start"]
                )

    def test_timeline_contains_empty_buckets(self):
        timeline = build_timeline([(1, "a"), (21, "b")], bucket_seconds=10, duration_seconds=30)
        self.assertEqual([item["count"] for item in timeline], [1, 0, 1])

    def test_timeline_keeps_event_on_exact_duration_boundary(self):
        timeline = build_timeline([(30, "片尾弹幕")], bucket_seconds=10, duration_seconds=30)
        self.assertEqual(len(timeline), 4)
        self.assertEqual(timeline[-1], {"start": 30, "end": 40, "count": 1})

    def test_full_analysis_returns_dashboard_shape(self):
        result = analyze_danmaku(self.items, duration_seconds=20, top_n=5)
        self.assertEqual(result["total_danmaku"], 5)
        self.assertIn("top_words", result)
        self.assertIn("timeline", result)
        self.assertIn("peak_segments", result)
        self.assertEqual(result["metrics"]["average_per_minute"], 15)

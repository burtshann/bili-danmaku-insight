from django.test import SimpleTestCase

from myapp.views import calculate_max_danmaku, process_text


class DanmakuAnalysisTests(SimpleTestCase):
    def test_process_text_returns_top_words(self):
        danmaku_list = [
            (1.0, "这个视频真的很好看"),
            (2.0, "视频内容很好看"),
            (3.0, "这个内容值得收藏"),
        ]

        result = process_text(danmaku_list)

        self.assertIn("words", result)
        self.assertIn("counts", result)
        self.assertEqual(len(result["words"]), len(result["counts"]))
        self.assertLessEqual(len(result["words"]), 5)

    def test_calculate_max_danmaku_uses_three_second_window(self):
        start_time, end_time, count = calculate_max_danmaku([2.1, 2.4, 3.1, 6.0, 6.2])

        self.assertEqual(start_time, 2)
        self.assertEqual(end_time, 5)
        self.assertEqual(count, 3)

from unittest.mock import patch

from django.test import TestCase

from myapp.models import AnalysisTask, DanmakuSummary
from myapp.services.bilibili import BilibiliRequestError
from myapp.tasks import execute_task


class AnalysisTaskExecutionTests(TestCase):
    def create_task(self):
        return AnalysisTask.objects.create(
            kind=AnalysisTask.Kind.ANALYSIS,
            source_url="https://www.bilibili.com/video/BV1xx411c7mD",
            parameters={
                "top_n": 5,
                "bucket_seconds": 10,
                "window_seconds": 3,
                "peak_count": 3,
            },
        )

    @patch("myapp.tasks.BilibiliClient.fetch")
    def test_execute_analysis_task_persists_result(self, fetch):
        fetch.return_value = {
            "metadata": {
                "bvid": "BV1xx411c7mD",
                "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
                "title": "任务测试视频",
                "owner_name": "测试 UP 主",
                "owner_id": "42",
                "cover_url": "",
                "duration_seconds": 60,
                "metadata": {"views": 1000},
            },
            "danmaku": [
                (1.1, "项目讲解很清楚"),
                (1.5, "项目讲解很清楚"),
                (12.0, "测试覆盖很完整"),
            ],
        }
        task = self.create_task()

        execute_task(task.pk)

        task.refresh_from_db()
        self.assertEqual(task.status, AnalysisTask.Status.SUCCESS)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.video.bvid, "BV1xx411c7mD")
        self.assertEqual(task.result["analysis"]["total_danmaku"], 3)
        self.assertTrue(DanmakuSummary.objects.filter(video=task.video).exists())

    @patch("myapp.tasks.BilibiliClient.fetch")
    def test_execute_analysis_task_records_expected_failure(self, fetch):
        fetch.side_effect = BilibiliRequestError("上游页面不可用")
        task = self.create_task()

        execute_task(task.pk)

        task.refresh_from_db()
        self.assertEqual(task.status, AnalysisTask.Status.FAILED)
        self.assertEqual(task.error_message, "上游页面不可用")

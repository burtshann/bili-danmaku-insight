import json
import tempfile
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from myapp.models import AnalysisTask, DanmakuSummary, Video


class ApiTests(TestCase):
    def setUp(self):
        cache.clear()

    def csrf_client(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/api/v1/csrf/")
        self.assertEqual(response.status_code, 200)
        return client, response.cookies["csrftoken"].value

    @patch("myapp.views.submit_task")
    def test_create_analysis_returns_pollable_task(self, submit_task):
        client, token = self.csrf_client()
        response = client.post(
            "/api/v1/analyses/",
            data=json.dumps({"url": "BV1xx411c7mD", "top_n": 10}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 202)
        payload = response.json()["task"]
        self.assertEqual(payload["status"], AnalysisTask.Status.PENDING)
        submit_task.assert_called_once()

        detail = client.get(f"/api/v1/tasks/{payload['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["task"]["id"], payload["id"])

    def test_create_analysis_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(
            "/api/v1/analyses/",
            data=json.dumps({"url": "BV1xx411c7mD"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(ANALYSIS_RATE_LIMIT=1)
    @patch("myapp.views.submit_task")
    def test_analysis_endpoint_is_rate_limited(self, submit_task):
        client, token = self.csrf_client()
        request = {
            "data": json.dumps({"url": "BV1xx411c7mD"}),
            "content_type": "application/json",
            "HTTP_X_CSRFTOKEN": token,
        }
        self.assertEqual(client.post("/api/v1/analyses/", **request).status_code, 202)
        response = client.post("/api/v1/analyses/", **request)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "rate_limited")

    def test_rejects_non_bilibili_url(self):
        client, token = self.csrf_client()
        response = client.post(
            "/api/v1/analyses/",
            data=json.dumps({"url": "https://example.com/video/BV1xx411c7mD"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_request")

    def test_history_detail_and_export(self):
        video = Video.objects.create(
            bvid="BV1xx411c7mD",
            source_url="https://www.bilibili.com/video/BV1xx411c7mD",
            title="测试视频",
            owner_name="测试UP主",
            duration_seconds=60,
        )
        summary = DanmakuSummary.objects.create(
            video=video,
            total_danmaku=12,
            top_words=[{"word": "测试", "count": 4}],
            timeline=[{"start": 0, "end": 10, "count": 3}],
            peak_segments=[{"start": 2, "end": 5, "count": 3}],
            metrics={"average_per_minute": 12, "peak_per_second": 1},
        )

        history = self.client.get("/api/v1/analyses/history/")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["items"][0]["analysis"]["id"], summary.pk)

        detail = self.client.get(f"/api/v1/analyses/{video.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["video"]["title"], "测试视频")

        with tempfile.TemporaryDirectory() as output_dir:
            with override_settings(DOWNLOAD_ROOT=output_dir):
                response = self.client.post(
                    "/api/v1/exports/",
                    data=json.dumps({"video_id": video.pk}),
                    content_type="application/json",
                )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["export"]["file_name"].endswith(".xlsx"))

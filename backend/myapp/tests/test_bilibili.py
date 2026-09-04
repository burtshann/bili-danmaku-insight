from unittest.mock import Mock

from django.test import SimpleTestCase
from requests import Response

from myapp.services.bilibili import (
    BilibiliRequestError,
    extract_cid,
    extract_metadata,
    parse_danmaku_xml,
    parse_initial_state,
    read_response_limited,
)

HTML = """
<html>
  <head><title>样例视频_哔哩哔哩_bilibili</title></head>
  <body>
    <script>
      window.__INITIAL_STATE__ = {
        "videoData": {
          "bvid": "BV1xx411c7mD",
          "aid": 123,
          "cid": 456,
          "title": "样例视频",
          "duration": 120,
          "pic": "https://i.example/cover.jpg",
          "owner": {"mid": 9, "name": "测试UP主"},
          "stat": {"view": 100, "danmaku": 20, "like": 10, "coin": 5}
        }
      };
    </script>
  </body>
</html>
"""


class BilibiliParserTests(SimpleTestCase):
    def test_parses_initial_state_and_metadata(self):
        state = parse_initial_state(HTML)
        self.assertEqual(extract_cid(state, HTML), "456")
        metadata = extract_metadata(
            state,
            HTML,
            "https://www.bilibili.com/video/BV1xx411c7mD",
        )
        self.assertEqual(metadata["title"], "样例视频")
        self.assertEqual(metadata["owner_name"], "测试UP主")
        self.assertEqual(metadata["metadata"]["views"], 100)

    def test_parses_danmaku_xml_and_skips_invalid_rows(self):
        xml = '<i><d p="1.5,1,25">第一条</d><d p="bad">跳过</d><d p="3.2">第二条</d></i>'
        self.assertEqual(parse_danmaku_xml(xml), [(1.5, "第一条"), (3.2, "第二条")])

    def test_rejects_empty_danmaku_xml(self):
        with self.assertRaises(BilibiliRequestError):
            parse_danmaku_xml("<i></i>")

    def test_rejects_oversized_external_response(self):
        response = Response()
        response.status_code = 200
        response._content = b"123456"
        response.raw = Mock()
        response.headers["Content-Length"] = "6"

        with self.assertRaises(BilibiliRequestError):
            read_response_limited(response, max_bytes=5, label="测试响应")

from django.test import SimpleTestCase

from myapp.services.validation import InputValidationError, extract_bvid, validate_bilibili_url


class BilibiliUrlValidationTests(SimpleTestCase):
    def test_accepts_bvid_and_normalizes_it(self):
        self.assertEqual(
            validate_bilibili_url("BV1xx411c7mD"),
            "https://www.bilibili.com/video/BV1xx411c7mD",
        )

    def test_accepts_supported_share_link(self):
        self.assertEqual(validate_bilibili_url("https://b23.tv/AbCd12"), "https://b23.tv/AbCd12")

    def test_rejects_lookalike_host(self):
        with self.assertRaises(InputValidationError):
            validate_bilibili_url(
                "https://bilibili.com.attacker.example/video/BV1xx411c7mD"
            )

    def test_rejects_credentials_and_custom_ports(self):
        invalid_values = [
            "https://user@www.bilibili.com/video/BV1xx411c7mD",
            "https://www.bilibili.com:8080/video/BV1xx411c7mD",
        ]
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(InputValidationError):
                validate_bilibili_url(value)

    def test_extracts_bvid_from_url(self):
        self.assertEqual(
            extract_bvid("https://www.bilibili.com/video/BV1xx411c7mD?p=1"),
            "BV1xx411c7mD",
        )

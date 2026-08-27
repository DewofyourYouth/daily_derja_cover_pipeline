import base64
import io
import json
import os
import unittest
from unittest.mock import patch

from PIL import Image

from brand import imagegen


def _encoded_png():
    buf = io.BytesIO()
    Image.new("RGB", (4, 3), "red").save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class OpenRouterImageTests(unittest.TestCase):
    def test_reference_slate_uses_three_quality_models(self):
        self.assertEqual(
            imagegen.choose_openrouter_models(3, has_references=True),
            [
                "google/gemini-3-pro-image",
                "openai/gpt-image-2",
                "black-forest-labs/flux.2-pro",
            ],
        )

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    @patch("brand.imagegen.urlopen")
    def test_image_request_includes_base64_reference(self, mocked_urlopen):
        mocked_urlopen.return_value = io.BytesIO(json.dumps({
            "data": [{"b64_json": _encoded_png(), "media_type": "image/png"}],
            "usage": {"cost": 0.04125},
        }).encode("utf-8"))

        result = imagegen.openrouter_image(
            "paint this person",
            [Image.new("RGB", (2, 2), "blue")],
            aspect_ratio="16:9",
            model="google/gemini-3-pro-image",
        )

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "google/gemini-3-pro-image")
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertTrue(payload["input_references"][0]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        ))
        self.assertEqual(result.size, (4, 3))
        self.assertEqual(imagegen.api_cost_usd(result), 0.04125)

    def test_image_without_cost_metadata_returns_none(self):
        self.assertIsNone(imagegen.api_cost_usd(Image.new("RGB", (2, 2))))


if __name__ == "__main__":
    unittest.main()

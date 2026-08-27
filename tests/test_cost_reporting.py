import unittest
from unittest.mock import patch

from PIL import Image

import cover
from brand.imagegen import API_COST_INFO_KEY


class CostReportingTests(unittest.TestCase):
    @patch("cover.log")
    def test_sums_exact_cost_across_variants(self, mocked_log):
        first = Image.new("RGB", (2, 2))
        second = Image.new("RGB", (2, 2))
        first.info[API_COST_INFO_KEY] = 0.04
        second.info[API_COST_INFO_KEY] = 0.0125

        cover._log_api_cost([first, second], api_used=True, provider="openrouter")

        mocked_log.assert_called_once_with("[cost] total API cost: $0.0525 USD")

    @patch("cover.log")
    def test_no_api_run_reports_zero(self, mocked_log):
        cover._log_api_cost()

        mocked_log.assert_called_once_with(
            "[cost] total API cost: $0.00 USD (no API calls)"
        )


if __name__ == "__main__":
    unittest.main()

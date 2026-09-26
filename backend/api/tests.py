import math
import time

from django.test import SimpleTestCase

from api.heatmap_cache import clear_cached, get_cached, set_cached
from api.views import _normalize_cell_value


class NormalizeCellValueTests(SimpleTestCase):
    def test_none_and_nan(self):
        self.assertIsNone(_normalize_cell_value(None))
        self.assertIsNone(_normalize_cell_value(float("nan")))

    def test_infinity(self):
        self.assertIsNone(_normalize_cell_value(float("inf")))
        self.assertIsNone(_normalize_cell_value(float("-inf")))

    def test_valid_number(self):
        self.assertEqual(_normalize_cell_value(12.5), 12.5)
        self.assertEqual(_normalize_cell_value("3.14"), 3.14)

    def test_invalid_value(self):
        self.assertIsNone(_normalize_cell_value("not-a-number"))


class HeatmapCacheTests(SimpleTestCase):
    def tearDown(self):
        clear_cached()

    def test_set_and_get(self):
        set_cached("heatmap:test:2026-01-01", {"ok": True})
        self.assertEqual(get_cached("heatmap:test:2026-01-01"), {"ok": True})

    def test_expires_after_ttl(self):
        set_cached("heatmap:test:2026-01-01", {"ok": True})
        time.sleep(0.05)
        self.assertIsNone(get_cached("heatmap:test:2026-01-01", ttl_seconds=0))

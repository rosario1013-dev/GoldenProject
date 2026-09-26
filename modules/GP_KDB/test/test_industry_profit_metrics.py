"""Unit tests for industry profit growth metrics (spec Tests 1–16)."""

from __future__ import annotations

import math
import unittest

from GP_KDB.industry_profit.metrics import (
    CAGR_PERIOD_3,
    CAGR_PERIOD_5,
    STATUS_BASE_PROFIT_NON_POSITIVE,
    STATUS_LOSS_TO_LOSS,
    STATUS_PROFITABLE,
    STATUS_PROFIT_TO_LOSS,
    STATUS_TURNED_PROFITABLE,
    added_profit,
    build_industry_metrics,
    calc_cagr,
    calc_growth_confidence,
    calc_growth_stability,
    calc_yoy_growth,
    contribution_shares,
    industry_profit_sum,
    percentile_ranks,
    safe_float,
)


class SafeFloatTests(unittest.TestCase):
    def test_null_nan_inf(self):
        self.assertIsNone(safe_float(None))
        self.assertIsNone(safe_float(float("nan")))
        self.assertIsNone(safe_float(float("inf")))
        self.assertIsNone(safe_float(float("-inf")))
        self.assertIsNone(safe_float("abc"))
        self.assertEqual(safe_float("12.5"), 12.5)


class YoYTests(unittest.TestCase):
    def test_1_normal_growth(self):
        growth, status = calc_yoy_growth(120, 100)
        self.assertAlmostEqual(growth, 20.0)
        self.assertEqual(status, STATUS_PROFITABLE)

    def test_2_previous_zero(self):
        growth, status = calc_yoy_growth(50, 0)
        self.assertIsNone(growth)
        self.assertEqual(status, STATUS_BASE_PROFIT_NON_POSITIVE)

    def test_3_loss_to_profit(self):
        growth, status = calc_yoy_growth(5, -10)
        self.assertIsNone(growth)
        self.assertEqual(status, STATUS_TURNED_PROFITABLE)

    def test_4_profit_to_loss(self):
        growth, status = calc_yoy_growth(-5, 10)
        self.assertIsNone(growth)
        self.assertEqual(status, STATUS_PROFIT_TO_LOSS)

    def test_5_loss_to_loss(self):
        growth, status = calc_yoy_growth(-5, -10)
        self.assertIsNone(growth)
        self.assertEqual(status, STATUS_LOSS_TO_LOSS)

    def test_16_negative_to_positive_no_bogus_pct(self):
        growth, status = calc_yoy_growth(5_000_000_000, -10_000_000_000)
        self.assertIsNone(growth)
        self.assertEqual(status, STATUS_TURNED_PROFITABLE)
        # Must NOT be -150%
        self.assertNotEqual(growth, -150)


class AggregationTests(unittest.TestCase):
    def test_6_industry_sum(self):
        total = industry_profit_sum([30e9, 20e9, 10e9])
        self.assertAlmostEqual(total, 60e9)

    def test_7_growth_uses_sum_not_average(self):
        # Company A: 100 -> 150 (+50%), B: 100 -> 100 (0%) — average would be 25%
        # Industry: 200 -> 250 = +25% if averaged wrongly wait:
        # Sum path: 250/200-1 = 25%. Average of (50%, 0%) = 25% — need unequal sizes.
        # A: 10->30 (+200%), B: 90->95 (~5.56%) — avg ~102.78%, sum 125/100-1 = 25%
        companies_prev = [10, 90]
        companies_curr = [30, 95]
        industry_prev = industry_profit_sum(companies_prev)
        industry_curr = industry_profit_sum(companies_curr)
        growth, _ = calc_yoy_growth(industry_curr, industry_prev)
        avg_company = (
            calc_yoy_growth(30, 10)[0] + calc_yoy_growth(95, 90)[0]
        ) / 2
        self.assertAlmostEqual(growth, 25.0)
        self.assertNotAlmostEqual(growth, avg_company)


class ContributionTests(unittest.TestCase):
    def test_8_positive_contributions_sum_to_100(self):
        shares, positive_sum, net = contribution_shares([100, 50, -30])
        self.assertAlmostEqual(positive_sum, 150)
        self.assertAlmostEqual(net, 120)
        self.assertAlmostEqual(shares[0], 100 / 150 * 100)
        self.assertAlmostEqual(shares[1], 50 / 150 * 100)
        self.assertAlmostEqual(shares[2], 0.0)
        self.assertAlmostEqual(sum(s for s in shares if s and s > 0), 100.0)


class CagrTests(unittest.TestCase):
    def test_9_three_year_cagr(self):
        # 70 -> 140 over 3 years ≈ 25.99%
        cagr = calc_cagr(140, 70, period=CAGR_PERIOD_3)
        self.assertIsNotNone(cagr)
        self.assertAlmostEqual(cagr, ((140 / 70) ** (1 / 3) - 1) * 100, places=6)

    def test_10_five_year_cagr(self):
        cagr = calc_cagr(140, 70, period=CAGR_PERIOD_5)
        self.assertIsNotNone(cagr)
        self.assertAlmostEqual(cagr, ((140 / 70) ** (1 / 5) - 1) * 100, places=6)

    def test_cagr_rejects_non_positive(self):
        self.assertIsNone(calc_cagr(100, -10, period=CAGR_PERIOD_3))
        self.assertIsNone(calc_cagr(-10, 100, period=CAGR_PERIOD_3))
        self.assertIsNone(calc_cagr(100, 0, period=CAGR_PERIOD_3))


class MissingDataTests(unittest.TestCase):
    def test_11_missing_year(self):
        growth, status = calc_yoy_growth(100, None)
        self.assertIsNone(growth)
        self.assertEqual(status, STATUS_BASE_PROFIT_NON_POSITIVE)
        self.assertIsNone(calc_cagr(100, None, period=CAGR_PERIOD_3))

    def test_12_null_data(self):
        self.assertIsNone(industry_profit_sum([None, None]))
        self.assertIsNone(added_profit(None, 10))

    def test_13_nan(self):
        growth, _ = calc_yoy_growth(float("nan"), 100)
        self.assertIsNone(growth)
        self.assertIsNone(safe_float(float("nan")))

    def test_14_infinity(self):
        growth, _ = calc_yoy_growth(float("inf"), 100)
        self.assertIsNone(growth)
        self.assertIsNone(calc_cagr(float("inf"), 50, period=CAGR_PERIOD_3))


class ConfidenceAndStabilityTests(unittest.TestCase):
    def test_15_single_company_lowers_confidence(self):
        low = calc_growth_confidence(company_count=1, years_available=5)
        high = calc_growth_confidence(company_count=86, years_available=5)
        self.assertLess(low, 60)
        self.assertGreater(high, 85)
        self.assertLess(low, high)

    def test_stability_prefers_consistent_growth(self):
        stable = calc_growth_stability([20, 25, 30, 28, 32])
        volatile = calc_growth_stability([-20, 100, -50, 80, 60])
        self.assertIsNotNone(stable)
        self.assertIsNotNone(volatile)
        self.assertGreater(stable, volatile)


class BuildMetricsTests(unittest.TestCase):
    def test_build_end_to_end(self):
        industries = [
            {
                "industry": "A",
                "company_count": 50,
                "current_profit": 140,
                "previous_profit": 100,
                "profit_3y_ago": 70,
                "profit_5y_ago": 50,
                "yearly_profits": {2022: 70, 2023: 85, 2024: 95, 2025: 100, 2026: 140},
            },
            {
                "industry": "B",
                "company_count": 3,
                "current_profit": 110,
                "previous_profit": 100,
                "profit_3y_ago": 90,
                "profit_5y_ago": 80,
                "yearly_profits": {2022: 80, 2023: 85, 2024: 90, 2025: 100, 2026: 110},
            },
            {
                "industry": "C",
                "company_count": 20,
                "current_profit": 80,
                "previous_profit": 100,
                "profit_3y_ago": 120,
                "profit_5y_ago": 130,
                "yearly_profits": {2022: 130, 2023: 125, 2024: 110, 2025: 100, 2026: 80},
            },
        ]
        rows = build_industry_metrics(industries, year=2026, period="yoy")
        self.assertEqual(len(rows), 3)
        by_name = {r["industry"]: r for r in rows}
        self.assertAlmostEqual(by_name["A"]["profit_growth_yoy"], 40.0)
        self.assertTrue(by_name["B"]["low_sample_size"])
        self.assertLess(by_name["B"]["growth_confidence"], by_name["A"]["growth_confidence"])
        contrib_sum = sum(
            r["profit_contribution"]
            for r in rows
            if r["profit_contribution"] and r["profit_contribution"] > 0
        )
        self.assertAlmostEqual(contrib_sum, 100.0, places=4)
        self.assertIsNotNone(by_name["A"]["growth_score"])
        pcts = percentile_ranks([40.0, 10.0, -20.0])
        self.assertGreater(pcts[0], pcts[1])
        self.assertGreater(pcts[1], pcts[2])


if __name__ == "__main__":
    unittest.main()

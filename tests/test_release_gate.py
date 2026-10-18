import unittest

from src.release_gate import THRESHOLDS, evaluate_utility_thresholds, decide_release


class ReleaseGateTests(unittest.TestCase):
    def good_metrics(self):
        return {
            "age_ks": 0.02,
            "balance_ks": 0.08,
            "balance_mean_relative_error": 0.04,
            "balance_p95_relative_error": 0.03,
            "outcome_yes_gap_pp": 1.0,
        }

    def test_metrics_inside_targets_pass(self):
        checks = evaluate_utility_thresholds(self.good_metrics())
        self.assertTrue(all(checks.values()))

    def test_exact_threshold_boundaries_pass(self):
        m = {
            "age_ks": THRESHOLDS["age_ks_max"],
            "balance_ks": THRESHOLDS["balance_ks_max"],
            "balance_mean_relative_error":
                THRESHOLDS["balance_mean_relative_error_max"],
            "balance_p95_relative_error":
                THRESHOLDS["balance_p95_relative_error_max"],
            "outcome_yes_gap_pp": THRESHOLDS["outcome_yes_gap_pp_max"],
        }
        self.assertTrue(all(evaluate_utility_thresholds(m).values()))

    def test_excessive_balance_ks_fails(self):
        m = self.good_metrics()
        m["balance_ks"] = THRESHOLDS["balance_ks_max"] + 0.001
        checks = evaluate_utility_thresholds(m)
        self.assertFalse(checks["balance_ks_within_target"])
        self.assertTrue(checks["age_ks_within_target"])

    def test_missing_mean_error_fails_closed(self):
        m = self.good_metrics()
        m["balance_mean_relative_error"] = None
        checks = evaluate_utility_thresholds(m)
        self.assertFalse(checks["balance_mean_error_within_target"])

    def test_large_outcome_gap_fails(self):
        m = self.good_metrics()
        m["outcome_yes_gap_pp"] = 5.0
        self.assertFalse(
            evaluate_utility_thresholds(m)["outcome_gap_within_target"]
        )



class ReleaseDecisionTests(unittest.TestCase):
    def test_pending_privacy_and_cobol_block_release(self):
        self.assertEqual(
            decide_release("PASS", "INCONCLUSIVE", "NOT_VERIFIED"),
            "NOT_APPROVED_PRIVACY_AND_COBOL_CHECKS_PENDING"
        )

    def test_integrity_failure_always_blocks(self):
        self.assertEqual(
            decide_release("FAIL", "PASS", "PASS"),
            "NOT_APPROVED_INTEGRITY_FAILURE"
        )

    def test_missing_cobol_blocks_release(self):
        self.assertEqual(
            decide_release("PASS", "PASS", "NOT_VERIFIED"),
            "NOT_APPROVED_COBOL_EXECUTION_PENDING"
        )

    def test_all_checks_allow_review_not_automatic_approval(self):
        self.assertEqual(
            decide_release("PASS", "PASS", "PASS"),
            "ELIGIBLE_FOR_HUMAN_REVIEW_NOT_AUTOMATIC_APPROVAL"
        )


if __name__ == "__main__":
    unittest.main()

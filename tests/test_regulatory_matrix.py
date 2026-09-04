import unittest

from fraudlens.core.compliance.regulatory_matrix import get_regulatory_context
from fraudlens.models.schemas import Decision


class RegulatoryMatrixTests(unittest.TestCase):
    def test_clear_has_no_regulatory_context(self) -> None:
        self.assertEqual(get_regulatory_context(Decision.CLEAR), [])

    def test_review_only_gets_rbi_monitoring_reference(self) -> None:
        refs = get_regulatory_context(Decision.REVIEW)
        frameworks = {r.framework for r in refs}
        self.assertEqual(frameworks, {"RBI Master Directions on Fraud Risk Management"})

    def test_block_gets_rbi_and_pmla(self) -> None:
        refs = get_regulatory_context(Decision.BLOCK)
        frameworks = {r.framework for r in refs}
        self.assertEqual(
            frameworks,
            {
                "RBI Master Directions on Fraud Risk Management",
                "Prevention of Money Laundering Act (PMLA), 2002",
            },
        )

    def test_block_and_report_gets_rbi_and_pmla(self) -> None:
        refs = get_regulatory_context(Decision.BLOCK_AND_REPORT)
        frameworks = {r.framework for r in refs}
        self.assertEqual(
            frameworks,
            {
                "RBI Master Directions on Fraud Risk Management",
                "Prevention of Money Laundering Act (PMLA), 2002",
            },
        )

    def test_cyber_enabled_fraud_type_adds_cert_in_at_block_severity(self) -> None:
        refs = get_regulatory_context(Decision.BLOCK_AND_REPORT, fraud_type="account_takeover_cluster")
        frameworks = {r.framework for r in refs}
        self.assertIn("CERT-In 2022 Cyber Incident Reporting Directions", frameworks)

    def test_non_cyber_fraud_type_does_not_add_cert_in(self) -> None:
        refs = get_regulatory_context(Decision.BLOCK_AND_REPORT, fraud_type="money_mule_network")
        frameworks = {r.framework for r in refs}
        self.assertNotIn("CERT-In 2022 Cyber Incident Reporting Directions", frameworks)

    def test_cyber_enabled_fraud_type_does_not_add_cert_in_below_block_severity(self) -> None:
        refs = get_regulatory_context(Decision.REVIEW, fraud_type="account_takeover_cluster")
        frameworks = {r.framework for r in refs}
        self.assertNotIn("CERT-In 2022 Cyber Incident Reporting Directions", frameworks)

    def test_every_reference_is_hedged_never_a_claim_of_actual_filing(self) -> None:
        """The one place a wrong claim is a real credibility risk — every
        reference must read as reference context, never as a completed
        regulatory action."""
        for decision in Decision:
            for fraud_type in (None, "account_takeover_cluster", "money_mule_network"):
                for ref in get_regulatory_context(decision, fraud_type):
                    lowered = ref.hedge.lower()
                    self.assertTrue(
                        "typically" in lowered or "not" in lowered,
                        f"Hedge for {ref.framework} does not read as reference-only: {ref.hedge!r}",
                    )
                    # An affirmative claim of a completed filing/report,
                    # not preceded by a negation, would misrepresent the
                    # system as having taken real regulatory action.
                    forbidden = ("this was reported", "this pattern was reported", "has been reported to")
                    for phrase in forbidden:
                        self.assertNotIn(phrase, lowered)


if __name__ == "__main__":
    unittest.main()

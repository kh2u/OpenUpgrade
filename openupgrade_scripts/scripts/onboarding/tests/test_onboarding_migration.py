# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestOnboardingMigration(TransactionCase):
    def _step(self, title):
        return self.env["onboarding.onboarding.step"].search(
            [("title", "=", title)], limit=1
        )

    def test_default_done_icon(self):
        """
        Test that the steps with the 19.0 default done_icon got the 20.0 default
        """
        steps = self.env["onboarding.onboarding.step"].browse(
            [
                self.env.ref(f"account.onboarding_onboarding_step_{name}").id
                for name in (
                    "company_data",
                    "base_document_layout",
                    "fiscal_year",
                    "chart_of_accounts",
                    "sales_tax",
                )
            ]
        )
        self.assertEqual(steps.mapped("done_icon"), ["star"] * 5)

    def test_converted_done_icon(self):
        """
        Test that a FontAwesome done_icon became a Material Symbols name
        """
        self.assertEqual(self._step("OU test trophy").done_icon, "trophy")

    def test_unknown_done_icon(self):
        """
        Test that a done_icon without a counterpart got the default
        """
        self.assertEqual(self._step("OU test unknown").done_icon, "star")

    def test_no_font_awesome_left(self):
        """
        Test that no done_icon is a FontAwesome class anymore
        """
        self.assertFalse(
            self.env["onboarding.onboarding.step"].search_count(
                [("done_icon", "=like", "fa-%")]
            )
        )

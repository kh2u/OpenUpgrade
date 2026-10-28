# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestWebMigration(TransactionCase):
    def test_res_company_report_layout(self):
        """
        Test that the table design of the removed report layouts has been kept in
        res.company#report_tables_id and that their companies use the standard layout
        """
        expected = {
            "striped": ("standard", "striped"),
            "boxed": ("standard", "boxed"),
            "bold": ("standard", "bold"),
            "bubble": ("bubble", "bubble"),
            "folder": ("folder", "striped"),
            "wave": ("wave", "striped"),
        }
        for layout, (new_layout, report_tables_id) in expected.items():
            with self.subTest(layout=layout):
                company = self.env["res.company"].search(
                    [("name", "=", f"Web {layout} layout company")]
                )
                self.assertEqual(
                    company.external_report_layout_id,
                    self.env.ref(f"web.external_layout_{new_layout}"),
                )
                self.assertEqual(company.report_tables_id, report_tables_id)

    def test_res_company_report_layout_unset(self):
        """
        Test that a company without report layout keeps the default table design
        """
        company = self.env.ref("base.main_company")
        self.assertFalse(company.external_report_layout_id)
        self.assertEqual(company.report_tables_id, "light")

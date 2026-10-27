# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


class TestAnalyticMigrationCommon(TransactionCase):
    def _get_test_plan_column(self):
        plan = self.env["account.analytic.plan"].search(
            [("name", "=", "OU Analytic Test Plan")]
        )
        self.assertEqual(len(plan), 1)
        return plan._strict_column_name()


@openupgrade_test
class TestAnalyticMigration(TestAnalyticMigrationCommon):
    def test_distribution_model_analytic_distribution(self):
        """
        Test that the distribution model without distribution got an empty one
        """
        model = self.env["account.analytic.distribution.model"].search(
            [("sequence", "=", 4242)]
        )
        self.assertEqual(len(model), 1)
        self.assertEqual(model.analytic_distribution, {})

    def test_plan_column_on_delete(self):
        """
        Test that the plan column created with `set null` now restricts deletion
        """
        field = self.env["ir.model.fields"].search(
            [
                ("model", "=", "account.analytic.line"),
                ("name", "=", self._get_test_plan_column()),
            ]
        )
        self.assertEqual(field.on_delete, "restrict")

    def test_analytic_plan_projects_name(self):
        """
        Test that the project plan got its new default name
        """
        self.assertEqual(
            self.env.ref("analytic.analytic_plan_projects").name, "Project Plan"
        )


@openupgrade_test
@tagged("post_install")
class TestAnalyticPostMigration(TestAnalyticMigrationCommon):
    def test_plan_column_foreign_key(self):
        """
        Test that the registry recreated the foreign key of the plan column with
        the new rule, once all the modules are loaded
        """
        self.env.cr.execute(
            """
            SELECT fk.confdeltype
            FROM pg_constraint fk
            JOIN pg_attribute a
                ON a.attrelid = fk.conrelid AND a.attnum = fk.conkey[1]
            WHERE fk.contype = 'f'
                AND fk.conrelid = 'account_analytic_line'::regclass
                AND a.attname = %s
            """,
            (self._get_test_plan_column(),),
        )
        self.assertEqual(self.env.cr.fetchall(), [("r",)])

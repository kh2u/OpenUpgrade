# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def account_analytic_distribution_model_analytic_distribution(env):
    """analytic_distribution is required in 20.0, and `_get_distribution` merges
    it with `|`, which fails on an unset value. Use an empty distribution: it
    has no effect, so the records are kept."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_distribution_model
        SET analytic_distribution = '{}'::jsonb
        WHERE analytic_distribution IS NULL
        """,
    )


def analytic_plan_columns_on_delete(env):
    """The plan columns (`x_plan<id>_id`) created by older versions have `set null`
    as on_delete, while new ones use `restrict`. Odoo's own `migrations/1.2` of
    analytic changes it, but the framework excluded it when migrating from 17.0
    (the columns didn't exist yet) and it doesn't run again afterwards, so
    databases migrated with OpenUpgrade still have `set null`. The registry
    recreates the foreign keys because their on delete rule differs from the
    field definition."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_fields
        SET on_delete = 'restrict'
        WHERE state = 'manual'
            AND ttype = 'many2one'
            AND relation = 'account.analytic.account'
            AND name ~ '^x_plan[0-9]+_id$'
            AND on_delete = 'set null'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    account_analytic_distribution_model_analytic_distribution(env)
    analytic_plan_columns_on_delete(env)

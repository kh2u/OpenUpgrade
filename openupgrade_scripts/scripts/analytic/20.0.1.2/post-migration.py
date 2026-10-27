# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def analytic_plan_projects_name(env):
    """analytic.analytic_plan_projects is renamed from 'Project' to 'Project Plan'.

    noupdate_changes.xml is not loaded because it only contains this name and
    the root plan is often renamed by users: it would overwrite their name.
    The translations of the old name are dropped with the jsonb replacement,
    they are filled again from the .po files after the migration scripts.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_plan aap
        SET name = jsonb_build_object('en_US', 'Project Plan')
        FROM ir_model_data imd
        WHERE imd.module = 'analytic'
            AND imd.name = 'analytic_plan_projects'
            AND imd.model = 'account.analytic.plan'
            AND imd.res_id = aap.id
            AND aap.name->>'en_US' = 'Project'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    analytic_plan_projects_name(env)

# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def ir_ui_view_visibility(env):
    """The key of public views is `public` in 20.0, and was an empty string in
    19.0. The ORM fills the NULL values with the new default, but not the empty
    strings, which are written when a page is published or made public in its
    properties: those views would be denied to all visitors."""
    openupgrade.logged_query(
        env.cr, "UPDATE ir_ui_view SET visibility = 'public' WHERE visibility = ''"
    )


@openupgrade.migrate()
def migrate(env, version):
    ir_ui_view_visibility(env)
    # the generic views are updated after this script, so they are still the ones of
    # 19.0 and can be compared with the copies made for the websites
    openupgrade.cow_templates_mark_if_equal_to_upstream(env.cr)

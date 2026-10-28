# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

# Table design that each v19 report layout came with. Layouts that are not listed
# (standard, custom views) keep the default 'light'.
_report_tables = {
    "striped": [
        "external_layout_striped",
        "external_layout_folder",
        "external_layout_wave",
    ],
    "boxed": ["external_layout_boxed"],
    "bold": ["external_layout_bold"],
    "bubble": ["external_layout_bubble"],
}

_removed_layouts = [
    "external_layout_striped",
    "external_layout_boxed",
    "external_layout_bold",
]


def res_company_report_layout(env):
    """
    The striped, boxed and bold report layouts are gone, and the table design is
    not a part of the layout anymore, but of res.company#report_tables_id.
    Keep the table design of every company and move the companies that used a
    removed layout to the standard layout.
    """
    for report_tables_id, layouts in _report_tables.items():
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE res_company
            SET report_tables_id = %s
            WHERE external_report_layout_id IN (
                SELECT res_id
                FROM ir_model_data
                WHERE module = 'web' AND model = 'ir.ui.view' AND name = ANY(%s)
            )
            """,
            (report_tables_id, layouts),
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET external_report_layout_id = (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'web'
                AND model = 'ir.ui.view'
                AND name = 'external_layout_standard'
        )
        WHERE external_report_layout_id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'web' AND model = 'ir.ui.view' AND name = ANY(%s)
        )
        """,
        (_removed_layouts,),
    )


@openupgrade.migrate()
def migrate(env, version):
    res_company_report_layout(env)

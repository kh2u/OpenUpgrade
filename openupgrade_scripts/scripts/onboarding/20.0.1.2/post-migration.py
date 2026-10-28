# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from openupgradelib import openupgrade

from odoo.upgrade_code.material_symbols_icons_mapping import FA_TO_MATERIAL

_logger = logging.getLogger(__name__)

DEFAULT_ICON = "star"


def onboarding_step_done_icon(env):
    """done_icon held a FontAwesome class (``fa-star``) in 19.0, 20.0 expects a
    Material Symbols name. Only the default changed, so the analysis does not
    report it. Convert the stored values with the mapping Odoo uses for its own
    sources, and use the default icon if there is no counterpart.
    """
    env.cr.execute(
        """
        SELECT id, done_icon
        FROM onboarding_onboarding_step
        WHERE done_icon LIKE %s
        """,
        ("fa-%",),
    )
    for step_id, done_icon in env.cr.fetchall():
        icon = FA_TO_MATERIAL.get(done_icon[3:], (None,))[0]
        if icon is None:
            _logger.warning(
                "onboarding.onboarding.step %s: no Material Symbols icon for "
                "done_icon %r, using %r",
                step_id,
                done_icon,
                DEFAULT_ICON,
            )
            icon = DEFAULT_ICON
        openupgrade.logged_query(
            env.cr,
            "UPDATE onboarding_onboarding_step SET done_icon = %s WHERE id = %s",
            (icon, step_id),
        )


@openupgrade.migrate()
def migrate(env, version):
    onboarding_step_done_icon(env)

# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from openupgradelib import openupgrade

from odoo.upgrade_code.material_symbols_icons_mapping import (
    FA_NOOP_MODIFIERS,
    FA_TO_MATERIAL,
    FA_UTIL_TO_OI,
    OI_TO_MATERIAL,
    OI_UTIL_CLASSES,
)

_logger = logging.getLogger(__name__)


def _lookup(cls):
    """Return (icon, filled) for an icon class such as ``fa-user``."""
    prefix, _sep, name = cls.partition("-")
    if prefix == "fa":
        return FA_TO_MATERIAL.get(name)
    if prefix == "oi":
        return OI_TO_MATERIAL.get(name)
    return None


def _modifier(cls):
    """Return the oi-* counterpart of a modifier class, '' if it carries nothing."""
    if cls in OI_UTIL_CLASSES:
        return cls
    prefix, _sep, name = cls.partition("-")
    if prefix != "fa":
        return None
    if name in FA_NOOP_MODIFIERS:
        return ""
    return FA_UTIL_TO_OI.get(name)


def _convert_css_class(css_class):
    """Convert a class string to (new class string, icon name or None).

    Port of ``_split_classes``, ``_build_classes``, ``_class_to_icon`` and
    ``_fa_classes_to_oi`` from ``odoo/upgrade_code/19.5-00-material-symbols-icons.py``,
    which cannot be imported. Return None if there is nothing to convert.
    """
    classes = css_class.split()
    if {"fa", "oi"}.isdisjoint(classes):
        return None
    icon, modifiers, others = None, [], []
    for cls in classes:
        if cls in ("fa", "oi"):
            continue
        if icon is None and (icon := _lookup(cls)):
            continue
        modifier = _modifier(cls)
        if modifier is None:
            others.append(cls)
        elif modifier:
            modifiers.append(modifier)
    if icon is None:
        if "fa" not in classes:
            return None
        name, filled = None, False
    else:
        name, filled = icon
    if filled:
        modifiers.append("oi-filled")
    return " ".join(["oi", *dict.fromkeys(modifiers), *others]), name


def auth_oauth_provider_css_class(env):
    """In 19.0 css_class holds FontAwesome classes (``fa fa-fw fa-sign-in``). 20.0
    renders an ``oi`` class and takes the icon name from the new field icon, so
    convert the stored values with the mapping Odoo uses for its own sources.
    """
    env.cr.execute("SELECT id, css_class FROM auth_oauth_provider")
    for provider_id, css_class in env.cr.fetchall():
        converted = css_class and _convert_css_class(css_class)
        if not converted:
            continue
        new_css_class, icon = converted
        if icon is None:
            _logger.warning(
                "auth.oauth.provider %s: no Material Symbols icon for css_class %r, "
                "keeping the default icon",
                provider_id,
                css_class,
            )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE auth_oauth_provider
            SET css_class = %s, icon = COALESCE(%s, icon)
            WHERE id = %s
            """,
            (new_css_class, icon, provider_id),
        )


@openupgrade.migrate()
def migrate(env, version):
    auth_oauth_provider_css_class(env)

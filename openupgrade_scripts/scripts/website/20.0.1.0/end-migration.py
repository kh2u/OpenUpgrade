# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import functools
import importlib.util
import logging
import os
import re
from html import escape

from openupgradelib import openupgrade
from psycopg2.extras import Json

from odoo import upgrade_code
from odoo.tools import split_every
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)

_social_networks = [
    "discord",
    "facebook",
    "github",
    "instagram",
    "linkedin",
    "tiktok",
    "twitter",
    "youtube",
]

# what the stored html fields are searched for, before being converted
_html_to_convert = r"\m(fa|oi)-|/website/social/|t-(esc|raw)=|/static/"
_static_image = re.compile(r"(/\w+/static/[^\s\"'<>()?#]+)\.(jpe?g|png|gif)\b")


def _load_transform_xml():
    """Return the function of Odoo's own upgrade script which converts the icons
    of the sources. Its name starts with a number, so it can't be imported."""
    try:
        spec = importlib.util.spec_from_file_location(
            "material_symbols_icons",
            os.path.join(upgrade_code.__path__[0], "19.5-00-material-symbols-icons.py"),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.transform_xml
    except Exception:
        _logger.warning(
            "The upgrade script of Odoo for the icons is not available: the icons "
            "stored in html fields are not converted to Material Symbols",
            exc_info=True,
        )
        return lambda content: content


@functools.cache
def _file_exists(path):
    try:
        file_path(path.lstrip("/"))
    except FileNotFoundError:
        return False
    return True


def _renamed_static_image(match):
    """Many images of 20.0 are in another format (e.g. `.jpg` became `.webp`) and
    kept their name: use the new file if the old one does not exist anymore."""
    path, extension = match.groups()
    if not _file_exists(f"{path}.{extension}"):
        for new_extension in ("webp", "svg"):
            if _file_exists(f"{path}.{new_extension}"):
                return f"{path}.{new_extension}"
    return match.group(0)


def _convert_html(content, transform_xml, social_urls):
    if isinstance(content, dict):  # translated, by language
        return {
            lang: _convert_html(text, transform_xml, social_urls)
            for lang, text in content.items()
        }
    content = transform_xml(content)
    # QWeb of 20.0 doesn't know t-esc and t-raw, which are t-out in 19.0
    content = re.sub(r"(\s)t-(?:esc|raw)=", r"\1t-out=", content)
    content = re.sub(
        r"/website/social/(\w+)",
        lambda match: escape(social_urls.get(match.group(1)) or "#"),
        content,
    )
    return _static_image.sub(_renamed_static_image, content)


def res_company_social_networks(env):
    """The urls of the social networks are fields of the company instead of the
    website. The company gets the one of its first website, if it has none."""
    for network in _social_networks:
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE res_company c SET social_{network} = w.social_{network}
            FROM (
                SELECT DISTINCT ON (company_id) company_id, social_{network}
                FROM website
                WHERE COALESCE(social_{network}, '') != ''
                ORDER BY company_id, sequence, id
            ) w
            WHERE w.company_id = c.id AND COALESCE(c.social_{network}, '') = ''
            """,
        )


def stored_html(env):
    """Convert what is stored in the html fields of the websites: the icons, the
    directives of QWeb, the links to the social networks of the website (replaced
    with its urls) and the images which changed of format. The views are
    converted only for the websites, the other ones are updated with the modules.
    Written with SQL, the ORM would copy the views and validate them."""
    transform_xml = _load_transform_xml()
    env.cr.execute(
        f"SELECT id, {', '.join(f'social_{n}' for n in _social_networks)} FROM website"
    )
    social_urls = {
        website_id: dict(zip(_social_networks, urls, strict=True))
        for website_id, *urls in env.cr.fetchall()
    }
    default_website_id = env.ref("base.default_website").id
    for model, field in env["website"]._get_html_fields():
        table = env[model]._table
        website = env[model]._fields.get("website_id")
        website_column = "website_id" if website and website.store else "NULL"
        views = "AND type = 'qweb' AND website_id IS NOT NULL"
        env.cr.execute(
            f"""
            SELECT id FROM {table}
            WHERE {field}::text ~ %s {views if model == "ir.ui.view" else ""}
            """,
            (_html_to_convert,),
        )
        for ids in split_every(1000, [row[0] for row in env.cr.fetchall()]):
            env.cr.execute(
                f"SELECT id, {website_column}, {field} FROM {table} WHERE id IN %s",
                (ids,),
            )
            for record_id, website_id, value in env.cr.fetchall():
                urls = social_urls.get(website_id or default_website_id, {})
                new_value = _convert_html(value, transform_xml, urls)
                if new_value != value:
                    env.cr.execute(
                        f"UPDATE {table} SET {field} = %s WHERE id = %s",
                        (
                            Json(new_value) if isinstance(value, dict) else new_value,
                            record_id,
                        ),
                    )
    env.invalidate_all()


def stored_cover_properties(env):
    """The covers of the records of the websites (blog, event, slide channel...) are
    JSON texts with the path of an image, which may have changed of format."""
    env.cr.execute(
        "SELECT DISTINCT model FROM ir_model_fields WHERE name = 'cover_properties'"
        " AND store"
    )
    for (model,) in env.cr.fetchall():
        table = model.replace(".", "_")
        if not openupgrade.table_exists(env.cr, table):
            continue
        env.cr.execute(
            f"""
            SELECT id, cover_properties FROM {table}
            WHERE cover_properties ~ '/static/'
            """
        )
        for record_id, value in env.cr.fetchall():
            new_value = _static_image.sub(_renamed_static_image, value)
            if new_value != value:
                env.cr.execute(
                    f"UPDATE {table} SET cover_properties = %s WHERE id = %s",
                    (new_value, record_id),
                )


@openupgrade.migrate()
def migrate(env, version):
    # the copies of the views must be reset before their html is converted
    openupgrade.cow_templates_replicate_upstream(env.cr)
    # the pages scheduled in post-migration, and the records of other modules
    env["website.page"]._manage_next_scheduled_action()
    res_company_social_networks(env)
    stored_html(env)
    stored_cover_properties(env)

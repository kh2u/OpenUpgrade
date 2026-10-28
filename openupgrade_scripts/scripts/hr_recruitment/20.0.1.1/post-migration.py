# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import ast
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

# definitions of the jobs of each company, and of the jobs of its applicants (a job
# may have no company, or another one than its applicants)
_company_properties = """
    WITH definitions AS (
        SELECT j.company_id, j.id AS job_id, j.applicant_properties_definition AS def
        FROM hr_job j
        WHERE j.company_id IS NOT NULL
        UNION
        SELECT a.company_id, j.id, j.applicant_properties_definition
        FROM hr_applicant a
        JOIN hr_job j ON j.id = a.job_id
        WHERE a.company_id IS NOT NULL
    ),
    elements AS (
        SELECT d.company_id, d.job_id, e.pos, e.elem
        FROM definitions d,
            jsonb_array_elements(d.def) WITH ORDINALITY AS e(elem, pos)
    )
"""

_templates_user_id = [
    "email_template_data_applicant_congratulations",
    "email_template_data_applicant_interest",
    "email_template_data_applicant_not_interested",
    "email_template_data_applicant_refuse",
]

_subtypes_no_description = [
    "mt_applicant_new",
    "mt_job_new",
    "mt_talent_new",
]


def hr_job_alias_defaults(env):
    """The defaults of the alias of a job hold its recruiter as `user_id`, which
    `hr.applicant` doesn't have anymore: the applicant of an incoming email would
    fail to be created, and 20.0 doesn't remove the key. Replace it with the
    employee of the user, as for the applicants. Users without employee can't be
    kept. The defaults are the text of a Python dictionary, hence done in Python."""
    env.cr.execute(
        """
        SELECT a.id, a.alias_defaults, j.company_id
        FROM mail_alias a
        JOIN ir_model m ON m.id = a.alias_model_id
        LEFT JOIN ir_model pm ON pm.id = a.alias_parent_model_id
        LEFT JOIN hr_job j ON j.id = a.alias_parent_thread_id AND pm.model = 'hr.job'
        WHERE m.model = 'hr.applicant' AND a.alias_defaults LIKE '%user_id%'
        """
    )
    lost = 0
    for alias_id, alias_defaults, job_company_id in env.cr.fetchall():
        defaults = ast.literal_eval(alias_defaults)
        if "user_id" not in defaults:
            continue
        user_id = defaults.pop("user_id")
        employee_id = False
        if user_id:
            env.cr.execute(
                """
                SELECT e.id
                FROM hr_employee e
                JOIN res_users u ON u.id = e.user_id
                WHERE e.user_id = %s
                ORDER BY COALESCE(e.company_id = %s, FALSE) DESC,
                    e.company_id = u.company_id DESC,
                    e.active DESC,
                    e.id
                LIMIT 1
                """,
                (user_id, job_company_id or defaults.get("company_id")),
            )
            employee_id = env.cr.fetchone()
            if employee_id:
                employee_id = employee_id[0]
            else:
                lost += 1
        defaults["recruiter_id"] = employee_id
        openupgrade.logged_query(
            env.cr,
            "UPDATE mail_alias SET alias_defaults = %s WHERE id = %s",
            (repr(defaults), alias_id),
        )
    if lost:
        _logger.warning(
            "%s email aliases have a recruiter without employee: they have no "
            "recruiter anymore",
            lost,
        )


def hr_job_favorite_recruiters(env):
    """Jobs are favorites of employees in 20.0 and were favorites of users in
    19.0. Keep all the employees of the users, so that they are still favorites
    when the user switches company. Users without employee can't be kept."""
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO job_favorite_recruiter_rel (job_id, recruiter_id)
        SELECT DISTINCT r.job_id, e.id
        FROM job_favorite_user_rel r
        JOIN hr_employee e ON e.user_id = r.user_id
        ON CONFLICT DO NOTHING
        """,
    )
    env.cr.execute(
        """
        SELECT COUNT(*) FROM job_favorite_user_rel r
        WHERE NOT EXISTS (SELECT 1 FROM hr_employee e WHERE e.user_id = r.user_id)
        """
    )
    if lost := env.cr.fetchone()[0]:
        _logger.warning(
            "%s favorite jobs of users without employee are not favorites anymore",
            lost,
        )


def res_company_applicant_properties_definition(env):
    """The definition of the applicant properties moves from the jobs to the
    companies: merge the ones of the jobs of each company, keeping the first one of
    each name (19.0 added the same to many jobs, and copying a job copies them).
    The values of the applicants are unchanged, but hidden without a definition."""
    env.cr.execute(
        _company_properties
        + """
        SELECT company_id, elem->>'name'
        FROM elements
        GROUP BY company_id, elem->>'name'
        HAVING COUNT(DISTINCT elem->>'type') > 1
        """
    )
    for company_id, name in env.cr.fetchall():
        _logger.warning(
            "res.company %s: the applicant property %s has jobs of different types, "
            "its values may be displayed wrongly",
            company_id,
            name,
        )
    openupgrade.logged_query(
        env.cr,
        _company_properties
        + """
        UPDATE res_company c
        SET applicant_properties_definition = merged.def
        FROM (
            SELECT company_id, jsonb_agg(elem ORDER BY job_id, pos) AS def
            FROM (
                SELECT DISTINCT ON (company_id, elem->>'name')
                    company_id, job_id, pos, elem
                FROM elements
                ORDER BY company_id, elem->>'name', job_id, pos
            ) first_elements
            GROUP BY company_id
        ) merged
        WHERE merged.company_id = c.id
        """,
    )
    env.cr.execute(
        """
        SELECT COUNT(*) FROM hr_applicant
        WHERE company_id IS NULL
            AND applicant_properties IS NOT NULL
            AND applicant_properties <> '{}'::jsonb
        """
    )
    if lost := env.cr.fetchone()[0]:
        _logger.warning(
            "%s applicants without company have property values: they have no "
            "definition anymore",
            lost,
        )


def hr_recruitment_degree_graduate(env):
    """20.0 renames the degree `Graduate` (score 0.5) to `Secondary Education`
    (score 0.3). noupdate_changes.xml doesn't change its name and score: it would
    overwrite a customized name, and fail on the unique name if another degree is
    already called so. The translations are dropped with the old name."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_recruitment_degree d
        SET name = jsonb_build_object('en_US', 'Secondary Education'),
            score = CASE WHEN d.score = 0.5 THEN 0.3 ELSE d.score END
        FROM ir_model_data imd
        WHERE imd.module = 'hr_recruitment'
            AND imd.name = 'degree_graduate'
            AND imd.model = 'hr.recruitment.degree'
            AND imd.res_id = d.id
            AND d.name->>'en_US' = 'Graduate'
            AND NOT EXISTS (
                SELECT 1 FROM hr_recruitment_degree
                WHERE name->>'en_US' = 'Secondary Education'
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env,
        "hr_recruitment",
        "20.0.1.1/noupdate_changes.xml",
        xml_transformation_filename="20.0.1.1/noupdate_changes-transformation.xml",
    )
    # the bodies of the templates use `object.user_id`, removed from hr.applicant
    openupgrade.delete_record_translations(
        env.cr, "hr_recruitment", _templates_user_id, ["body_html"]
    )
    # the descriptions of the subtypes are removed, not only in English
    openupgrade.delete_record_translations(
        env.cr, "hr_recruitment", _subtypes_no_description, ["description"]
    )
    hr_job_alias_defaults(env)
    hr_job_favorite_recruiters(env)
    res_company_applicant_properties_definition(env)
    hr_recruitment_degree_graduate(env)

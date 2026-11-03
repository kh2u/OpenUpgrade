# Copyright Odoo Community Association (OCA)
# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

_renamed_models = [("hr.contract.type", "hr.employee.type")]

_renamed_tables = [("hr_contract_type", "hr_employee_type")]

_renamed_fields = [
    ("hr.job", "hr_job", "contract_type_id", "employee_type_id"),
    ("hr.version", "hr_version", "contract_type_id", "employee_type_id"),
    ("hr.employee", "hr_employee", "contract_type_id", "employee_type_id"),
]


def hr_version_tz(env):
    """`tz` is stored on the version in 20.0: left to the ORM, all versions would get
    'UTC'. 19.0 took the timezone of the working hours, else the one of the employee,
    else the one of the working hours of the company: do the same."""
    openupgrade.add_columns(
        env, [("hr.version", "tz", "selection", None, "hr_version")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version v
        SET tz = COALESCE(
            (SELECT tz FROM resource_calendar WHERE id = v.resource_calendar_id),
            (SELECT r.tz FROM hr_employee e
                JOIN resource_resource r ON r.id = e.resource_id
                WHERE e.id = v.employee_id),
            (SELECT c.tz FROM res_company co JOIN resource_calendar c
                ON c.id = co.resource_calendar_id WHERE co.id = v.company_id),
            'UTC'
        )
        """,
    )
    env.cr.execute(
        """
        SELECT COUNT(*) FROM hr_version v
        JOIN hr_employee e ON e.id = v.employee_id
        JOIN resource_resource r ON r.id = e.resource_id
        WHERE v.tz != r.tz
        """
    )
    _logger.info("%s versions differ in tz from their employee", env.cr.fetchone()[0])


def hr_job_company(env):
    """`company_id` is required in 20.0: the ORM would give the main company to all
    jobs without one, failing on `unique (name, company_id, department_id)` as a
    missing company never conflicted. Use the company of the department, else the
    only one of the versions, else the main one; a conflicting name gets the job id."""
    openupgrade.logged_query(
        env.cr,
        """
        WITH job AS (
            SELECT j.id, j.name, j.department_id, j.company_id AS old_company_id,
                COALESCE(j.company_id, d.company_id,
                    (SELECT MIN(v.company_id) FROM hr_version v WHERE v.job_id = j.id
                        HAVING COUNT(DISTINCT v.company_id) = 1),
                    (SELECT u.company_id FROM res_users u WHERE u.id = %s)
                ) AS company_id
            FROM hr_job j
            LEFT JOIN hr_department d ON d.id = j.department_id
        ),
        ranked AS (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY name, company_id, department_id
                ORDER BY old_company_id IS NULL, id
            ) > 1 AND department_id IS NOT NULL AS conflict
            FROM job
        )
        UPDATE hr_job j
        SET company_id = r.company_id,
            name = CASE WHEN r.conflict THEN (
                SELECT jsonb_object_agg(k, v || ' (' || j.id || ')')
                FROM jsonb_each_text(j.name) AS t(k, v)
            ) ELSE j.name END
        FROM ranked r
        WHERE r.id = j.id AND j.company_id IS NULL
        RETURNING j.id, r.conflict
        """,
        (env.uid,),
    )
    if renamed := [job_id for job_id, conflict in env.cr.fetchall() if conflict]:
        _logger.warning("Jobs %s got their id in their name to stay unique", renamed)


def hr_job_recruiter(env):
    """The recruiter is an employee (`recruiter_id`) in 20.0, a user (`user_id`) in
    19.0: use the employee of the user, preferring the one of the company of the job,
    then of the main company of the user. Users without employee can't be kept."""
    openupgrade.add_columns(
        env, [("hr.job", "recruiter_id", "many2one", None, "hr_job")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_job j
        SET recruiter_id = (
            SELECT e.id FROM hr_employee e WHERE e.user_id = j.user_id
            ORDER BY e.company_id = j.company_id DESC,
                e.company_id = u.company_id DESC, e.active DESC, e.id
            LIMIT 1
        )
        FROM res_users u
        WHERE u.id = j.user_id
        """,
    )
    env.cr.execute(
        "SELECT COUNT(*) FROM hr_job WHERE user_id IS NOT NULL AND recruiter_id IS NULL"
    )
    if lost := env.cr.fetchone()[0]:
        _logger.warning("%s jobs have a recruiter without employee: dropped", lost)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _renamed_models)
    openupgrade.rename_tables(env.cr, _renamed_tables)
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, [("hr.version", "fixed_term", "boolean", False)])
    # a version without working hours is fully flexible, which the ORM would lose
    openupgrade.copy_columns(
        env.cr, {"hr_version": [("resource_calendar_id", None, None)]}
    )
    hr_version_tz(env)
    hr_job_company(env)
    hr_job_recruiter(env)

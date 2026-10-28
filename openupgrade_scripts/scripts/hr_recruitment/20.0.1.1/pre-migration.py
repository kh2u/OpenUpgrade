# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def hr_applicant_duration_tracking(env):
    """`duration_tracking` is stored in 20.0 as `{previous stage id: minutes, "s":
    current stage id, "d": date the record entered it}`, not computed on read from
    the tracking values anymore. Left to the ORM, the history would be lost: rebuild
    it from them. The time in a stage runs from the previous tracking value (or the
    creation of the record) to the one that moved the record out of it. No stage
    is stored under "0", as in 20.0. Unlike 19.0, the time since a refusal is not
    deducted from the current stage."""
    openupgrade.add_columns(
        env, [("hr.applicant", "duration_tracking", "json", None, "hr_applicant")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        WITH trackings AS (
            SELECT m.res_id,
                v.old_value_integer,
                v.create_date,
                LAG(v.create_date) OVER w AS previous_date,
                LAST_VALUE(v.create_date) OVER (
                    w ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_date
            FROM mail_tracking_value v
            JOIN mail_message m ON m.id = v.mail_message_id
            WHERE v.field_id = (
                    SELECT id
                    FROM ir_model_fields
                    WHERE model = 'hr.applicant' AND name = 'stage_id'
                )
                AND m.model = 'hr.applicant'
            WINDOW w AS (PARTITION BY m.res_id ORDER BY v.id)
        ),
        stage_time AS (
            SELECT t.res_id,
                COALESCE(t.old_value_integer, 0)::text AS stage,
                ROUND(SUM(EXTRACT(EPOCH FROM t.create_date - COALESCE(
                    t.previous_date, r.create_date, t.create_date
                ))) / 60)::integer AS minutes,
                MAX(t.last_date) AS last_date
            FROM trackings t
            JOIN hr_applicant r ON r.id = t.res_id
            GROUP BY t.res_id, COALESCE(t.old_value_integer, 0)
        ),
        history AS (
            SELECT res_id,
                jsonb_object_agg(stage, minutes) AS minutes_per_stage,
                MAX(last_date) AS last_date
            FROM stage_time
            GROUP BY res_id
        )
        UPDATE hr_applicant r
        SET duration_tracking = COALESCE(h.minutes_per_stage, '{}'::jsonb)
            || jsonb_build_object(
                's', COALESCE(r.stage_id, 0),
                'd', to_char(
                    COALESCE(h.last_date, r.create_date, NOW() AT TIME ZONE 'UTC'),
                    'YYYY-MM-DD HH24:MI:SS'
                )
            )
        FROM hr_applicant rr
        LEFT JOIN history h ON h.res_id = rr.id
        WHERE rr.id = r.id
        """,
    )


def hr_applicant_recruiter(env):
    """The recruiter is an employee (`recruiter_id`) in 20.0 and was a user
    (`user_id`) in 19.0. Left to the ORM, the new column would be computed from
    the job and the recruiters set by hand would be lost: fill it with the
    employee of the user, preferring the one of the company of the applicant, then
    of the main company of the user, then the first active one.
    Users without employee can't be kept."""
    openupgrade.add_columns(
        env, [("hr.applicant", "recruiter_id", "many2one", None, "hr_applicant")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_applicant a
        SET recruiter_id = (
            SELECT e.id
            FROM hr_employee e
            WHERE e.user_id = a.user_id
            ORDER BY COALESCE(e.company_id = a.company_id, FALSE) DESC,
                e.company_id = u.company_id DESC,
                e.active DESC,
                e.id
            LIMIT 1
        )
        FROM res_users u
        WHERE u.id = a.user_id
        """,
    )
    env.cr.execute(
        """
        SELECT COUNT(*) FROM hr_applicant
        WHERE user_id IS NOT NULL AND recruiter_id IS NULL
        """
    )
    if lost := env.cr.fetchone()[0]:
        _logger.warning(
            "%s applicants have a recruiter without employee: they have no "
            "recruiter anymore",
            lost,
        )


def hr_recruitment_degree_diploma(env):
    """The names of the degrees are unique: the new degree `Diploma` would fail on
    the constraint if one has the same name. Give the xmlid to that one instead."""
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        SELECT 'hr_recruitment', 'degree_diploma', 'hr.recruitment.degree', id, TRUE
        FROM hr_recruitment_degree
        WHERE name->>'en_US' = 'Diploma'
        ORDER BY id
        LIMIT 1
        ON CONFLICT (module, name) DO NOTHING
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    hr_applicant_duration_tracking(env)
    hr_applicant_recruiter(env)
    hr_recruitment_degree_diploma(env)

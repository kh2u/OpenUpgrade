# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

_duration_tracking_models = [
    ("project.task", "project_task"),
    ("project.project", "project_project"),
]


def project_duration_tracking(env):
    """`duration_tracking` is stored in 20.0 and its format changed: 19.0 computed
    on read `{stage id: seconds}` from the stage tracking values, while 20.0 keeps
    `{previous stage id: minutes, "s": current stage id, "d": date the record
    entered it}` and only updates it on stage changes, never reading the history
    again. Left to the ORM, the whole history would be lost and `d` would be the
    migration date, so rebuild it from the tracking values as 19.0 did: the time
    spent in a stage is the time from the previous tracking value (or from the
    creation of the record) to the tracking value that moved the record out of it.
    A missing previous stage is stored under "0", as 20.0 does for no stage.
    `project.project.date_last_stage_update` is new and takes the same date."""
    openupgrade.add_columns(
        env,
        [
            (model, "duration_tracking", "json", None, table)
            for model, table in _duration_tracking_models
        ]
        + [
            (
                "project.project",
                "date_last_stage_update",
                "datetime",
                None,
                "project_project",
            )
        ],
    )
    for model, table in _duration_tracking_models:
        openupgrade.logged_query(
            env.cr,
            f"""
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
                        WHERE model = %(model)s AND name = 'stage_id'
                    )
                    AND m.model = %(model)s
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
                JOIN {table} r ON r.id = t.res_id
                GROUP BY t.res_id, COALESCE(t.old_value_integer, 0)
            ),
            history AS (
                SELECT res_id,
                    jsonb_object_agg(stage, minutes) AS minutes_per_stage,
                    MAX(last_date) AS last_date
                FROM stage_time
                GROUP BY res_id
            )
            UPDATE {table} r
            SET duration_tracking = COALESCE(h.minutes_per_stage, '{{}}'::jsonb)
                || jsonb_build_object(
                    's', COALESCE(r.stage_id, 0),
                    'd', to_char(
                        COALESCE(h.last_date, r.create_date, NOW() AT TIME ZONE 'UTC'),
                        'YYYY-MM-DD HH24:MI:SS'
                    )
                )
            FROM {table} rr
            LEFT JOIN history h ON h.res_id = rr.id
            WHERE rr.id = r.id
            """,
            {"model": model},
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE project_project
        SET date_last_stage_update = (duration_tracking->>'d')::timestamp
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    project_duration_tracking(env)

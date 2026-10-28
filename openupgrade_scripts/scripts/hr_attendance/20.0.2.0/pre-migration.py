# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def attendance_validation(env):
    """Map "manager approves overtime" to "manager validates attendances".

    The new required hr.attendance#state is not the overtime approval, 19.0
    attendances are always valid. In the companies with manual validation only the
    attendances waiting for the manager (open or with overtime to approve) are drafts,
    all others are validated so that no time rule runs on the history in 20.0.
    """
    openupgrade.add_columns(
        env,
        [
            (
                "res.company",
                "attendance_validation",
                "selection",
                "no_validation",
                "res_company",
            ),
            ("hr.attendance", "state", "selection", "validated", "hr_attendance"),
        ],
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET attendance_validation = 'manual_validation'
        WHERE attendance_overtime_validation = 'by_manager'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance ha
        SET state = 'draft'
        FROM hr_employee he
        JOIN res_company rc ON rc.id = he.company_id
        WHERE he.id = ha.employee_id
            AND rc.attendance_validation = 'manual_validation'
            AND (ha.check_out IS NULL OR ha.overtime_status = 'to_approve')
        """,
    )


def hr_attendance_break_duration(env):
    """Keep worked_hours, it deducted the lunch break of the schedule in 19.0.

    20.0 deducts break_duration and ignores the schedule, so fill it with the deducted
    time and a recomputation of worked_hours gives the same value.
    """
    openupgrade.add_columns(
        env,
        [("hr.attendance", "break_duration", "float", None, "hr_attendance", "float8")],
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance
        SET break_duration = LEAST(
            EXTRACT(EPOCH FROM check_out - check_in) / 3600 - worked_hours,
            EXTRACT(EPOCH FROM check_out - check_in) / 3600
        )
        WHERE check_out IS NOT NULL
            AND EXTRACT(EPOCH FROM check_out - check_in) / 3600 - worked_hours > 0.001
        """,
    )


def hr_attendance_day_of_date(env):
    """Fill the new stored day_of_date (Monday is 0) from date without the ORM."""
    openupgrade.add_columns(
        env, [("hr.attendance", "day_of_date", "selection", None, "hr_attendance")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance
        SET day_of_date = (EXTRACT(ISODOW FROM date)::integer - 1)::varchar
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    attendance_validation(env)
    hr_attendance_break_duration(env)
    hr_attendance_day_of_date(env)

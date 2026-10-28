# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def hr_attendance_work_entry_type(env):
    """The default of the new required hr.attendance#work_entry_type_id is computed once
    for the whole table from the current company: use the one of the employee's company.

    SQL because writing attendances through the ORM runs the time rules.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance ha
        SET work_entry_type_id = rc.attendance_work_entry_type_id
        FROM hr_employee he
        JOIN res_company rc ON rc.id = he.company_id
        WHERE he.id = ha.employee_id
            AND rc.attendance_work_entry_type_id IS NOT NULL
            AND ha.work_entry_type_id IS DISTINCT FROM rc.attendance_work_entry_type_id
        """,
    )


def hr_time_rule_default_rules(env):
    """The overtime rule sets of 19.0 are not migrated, the time rules of hr_work_entry
    replace them. Unlike the rule sets, which only applied to the contracts they were
    assigned to, the default rules apply to all employees.

    Without any rule set in use, archive the rules shipped by hr_work_entry so that
    nothing changes. Otherwise keep them and take over the tolerances of the 19.0
    default rule, unless rule sets of companies show that the setup is more complex.
    """
    env.cr.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM hr_version hv
            JOIN hr_attendance_overtime_ruleset rs ON rs.id = hv.ruleset_id
            WHERE hv.active AND rs.active
        )
        """
    )
    if not env.cr.fetchone()[0]:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE hr_time_rule
            SET active = FALSE
            WHERE id IN (
                SELECT res_id FROM ir_model_data
                WHERE module = 'hr_work_entry' AND model = 'hr.time.rule'
            )
            """,
        )
        _logger.info(
            "No overtime rule set was in use: archived the %s time rules shipped "
            "with hr_work_entry. Unarchive them in Attendances > Configuration > "
            "Automatic Rules to compute overtime.",
            env.cr.rowcount,
        )
        return
    env.cr.execute(
        """
        SELECT rc.name
        FROM hr_attendance_overtime_ruleset rs
        JOIN res_company rc ON rc.id = rs.company_id
        WHERE rs.active
        """
    )
    company_names = [name for (name,) in env.cr.fetchall()]
    if company_names:
        _logger.warning(
            "Overtime rule sets of the companies %s are not migrated: create the "
            "equivalent company rules in Attendances > Configuration > Automatic "
            "Rules and set the tolerances of the default rule.",
            ", ".join(company_names),
        )
    else:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE hr_time_rule htr
            SET employer_tolerance = hor.employer_tolerance,
                employee_tolerance = hor.employee_tolerance
            FROM ir_model_data new_imd, ir_model_data old_imd,
                hr_attendance_overtime_rule hor
            WHERE new_imd.module = 'hr_work_entry'
                AND new_imd.name = 'hr_time_rule_employee_schedule'
                AND new_imd.model = 'hr.time.rule'
                AND htr.id = new_imd.res_id
                AND old_imd.module = 'hr_attendance'
                AND old_imd.name = 'hr_attendance_overtime_employee_schedule_rule'
                AND old_imd.model = 'hr.attendance.overtime.rule'
                AND hor.id = old_imd.res_id
            """,
        )
    env.cr.execute(
        """
        SELECT COUNT(*)
        FROM hr_employee he
        LEFT JOIN hr_version hv ON hv.id = he.current_version_id
        LEFT JOIN hr_attendance_overtime_ruleset rs
            ON rs.id = hv.ruleset_id AND rs.active
        WHERE he.active AND rs.id IS NULL
        """
    )
    (employee_count,) = env.cr.fetchone()
    if employee_count:
        _logger.warning(
            "%s active employees had no overtime rule set in 19.0: the default time "
            "rules now apply to them as well.",
            employee_count,
        )


@openupgrade.migrate()
def migrate(env, version):
    hr_attendance_work_entry_type(env)
    hr_time_rule_default_rules(env)

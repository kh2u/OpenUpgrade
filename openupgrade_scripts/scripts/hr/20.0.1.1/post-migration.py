# Copyright Odoo Community Association (OCA)
# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

# v19 employee_type selection value -> v20 hr.employee.type record
_employee_type_xmlids = {
    "employee": "hr.contract_type_employee",
    "student": "hr.contract_type_student",
    "trainee": "hr.contract_type_intern",
}

# v19 employee_type selection value -> v20 type to create, if a version has it
_new_types = {"worker": "Worker", "contractor": "Contractor", "freelance": "Freelancer"}

# calendar of the versions that are fully flexible
_flexible = {"calendar_type": "undefined", "hours_per_week": 0, "hours_per_day": 0}

# v19 contract types without counterpart in v20
_obsolete_types = ["permanent", "temporary", "full_time", "part_time", "statutory"]


def hr_version_employee_type(env):
    # temporary contracts are now flagged by fixed_term
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version version
        SET fixed_term = TRUE, employee_type_id = NULL
        FROM ir_model_data imd
        WHERE imd.model = 'hr.employee.type'
            AND imd.module = 'hr'
            AND imd.name = 'contract_type_temporary'
            AND imd.res_id = version.employee_type_id
        """,
    )
    # types without v20 counterpart are deleted below, unless jobs use them
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version version
        SET employee_type_id = NULL
        FROM ir_model_data imd
        WHERE imd.model = 'hr.employee.type'
            AND imd.module = 'hr'
            AND imd.name IN (
                'contract_type_permanent', 'contract_type_full_time',
                'contract_type_part_time', 'contract_type_statutory'
            )
            AND imd.res_id = version.employee_type_id
        """,
    )
    employee_type_column = openupgrade.get_legacy_name("employee_type")
    if not openupgrade.column_exists(env.cr, "hr_version", "employee_type"):
        return
    openupgrade.rename_columns(
        env.cr, {"hr_version": [("employee_type", employee_type_column)]}
    )
    employee_types = {
        value: env.ref(xmlid, raise_if_not_found=False)
        for value, xmlid in _employee_type_xmlids.items()
    }
    EmployeeType = env["hr.employee.type"]
    for value, name in _new_types.items():
        env.cr.execute(
            f"""
            SELECT 1 FROM hr_version
            WHERE employee_type_id IS NULL AND {employee_type_column} = %s
            """,
            (value,),
        )
        if env.cr.rowcount:
            employee_types[value] = EmployeeType.search(
                [("name", "=", name)], limit=1
            ) or EmployeeType.create({"name": name})
    for value, employee_type in employee_types.items():
        if not employee_type:
            continue
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE hr_version
            SET employee_type_id = %s
            WHERE employee_type_id IS NULL AND {employee_type_column} = %s
            """,
            (employee_type.id, value),
        )


def hr_employee_type_obsolete(env):
    """The obsolete types are noupdate records, which Odoo doesn't delete. No version
    has them anymore: delete those that no job has, as the type of a job is info."""
    Job = env["hr.job"].with_context(active_test=False)
    unused = []
    for name in _obsolete_types:
        xmlid = f"hr.contract_type_{name}"
        employee_type = env.ref(xmlid, raise_if_not_found=False)
        if not employee_type:
            continue
        if jobs := Job.search_count([("employee_type_id", "=", employee_type.id)]):
            _logger.warning("Employee type %s is kept: %s jobs have it", xmlid, jobs)
        else:
            unused.append(xmlid)
    openupgrade.delete_records_safely_by_xml_id(env, unused)


def hr_version_fully_flexible(env):
    """A version without working hours is fully flexible in 19.0, which 20.0 expresses
    with a flexible calendar without hours. The ORM gave them the default calendar of
    the main company: give them such a calendar of their own company instead."""
    legacy = openupgrade.get_legacy_name("resource_calendar_id")
    env.cr.execute(f"SELECT DISTINCT company_id FROM hr_version WHERE {legacy} IS NULL")
    Calendar = env["resource.calendar"]
    for (company_id,) in env.cr.fetchall():
        calendar = Calendar.search(
            [(k, "=", v) for k, v in _flexible.items()]
            + [("company_id", "=", company_id)],
            limit=1,
        ) or Calendar.with_company(company_id).create(
            {**_flexible, "name": "Fully Flexible", "company_id": company_id}
        )
        openupgrade.logged_query(
            env.cr,
            f"UPDATE hr_version SET resource_calendar_id = %s WHERE {legacy} IS NULL "
            "AND company_id IS NOT DISTINCT FROM %s",
            (calendar.id, company_id),
        )
    # the resource of an employee follows its current version in 20.0 (stored
    # computed fields, not computed by the update)
    openupgrade.logged_query(
        env.cr,
        "UPDATE resource_resource r SET tz = v.tz, "
        "calendar_id = v.resource_calendar_id FROM hr_employee e "
        "JOIN hr_version v ON v.id = e.current_version_id WHERE e.resource_id = r.id",
    )


def hr_employee_departure(env):
    """The departure is kept on the versions in 19.0 (copied to all the versions of an
    employee), it is a model in 20.0: create one for each employee, date, reason and
    description. Mark them applied, else the cron would archive the employees and
    delete their versions after the departure, e.g. when they came back."""
    env.cr.execute(
        "SELECT COUNT(*) FROM hr_version "
        "WHERE (departure_date IS NULL) != (departure_reason_id IS NULL)"
    )
    if ignored := env.cr.fetchone()[0]:
        _logger.warning("%s versions have only a departure date or reason", ignored)
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO hr_employee_departure (
            employee_id, departure_reason_id, departure_description, dismissal_date,
            departure_date, action_date, apply_date, last_contract_date_end, create_uid,
            create_date, write_uid, write_date
        )
        SELECT DISTINCT v.employee_id, v.departure_reason_id, v.departure_description,
            v.departure_date, v.departure_date, v.departure_date + 1, v.departure_date,
            (SELECT p.contract_date_end FROM hr_version p
                WHERE p.employee_id = v.employee_id
                    AND p.date_version <= v.departure_date
                ORDER BY p.date_version DESC LIMIT 1),
            %(uid)s, NOW() AT TIME ZONE 'UTC', %(uid)s, NOW() AT TIME ZONE 'UTC'
        FROM hr_version v
        WHERE v.employee_id IS NOT NULL
            AND v.departure_date IS NOT NULL AND v.departure_reason_id IS NOT NULL
        """,
        {"uid": env.uid},
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version v
        SET departure_id = d.id
        FROM hr_employee_departure d
        WHERE d.employee_id = v.employee_id
            AND d.departure_date = v.departure_date
            AND d.departure_reason_id = v.departure_reason_id
            AND d.departure_description IS NOT DISTINCT FROM v.departure_description
        """,
    )


def hr_employee_current_version_fields(env):
    """`additional_note` and `contract_template_id` are fields of the employee in
    20.0, they were the ones of its current version in 19.0."""
    openupgrade.logged_query(
        env.cr,
        "UPDATE hr_employee e SET additional_note = v.additional_note, "
        "contract_template_id = v.contract_template_id FROM hr_version v "
        "WHERE v.id = e.current_version_id",
    )


def hr_selection_values(env):
    """`other` is not a gender anymore and `coach` not a responsible of activity plans
    anymore: empty the first, let people choose when the plan is launched."""
    openupgrade.logged_query(
        env.cr, "UPDATE hr_version SET sex = NULL WHERE sex = 'other'"
    )
    openupgrade.logged_query(
        env.cr,
        "UPDATE mail_activity_plan_template SET responsible_type = 'on_demand' "
        "WHERE responsible_type = 'coach'",
    )


@openupgrade.migrate()
def migrate(env, version):
    hr_version_employee_type(env)
    hr_employee_type_obsolete(env)
    hr_version_fully_flexible(env)
    hr_employee_departure(env)
    hr_employee_current_version_fields(env)
    hr_selection_values(env)
    # needed: it deactivates the rules of base on bank accounts, which hr skips as base
    # created them in this upgrade, else internal users read the ones of employees
    openupgrade.load_data(env, "hr", "20.0.1.1/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr, "hr", ["contract_type_seasonal"], ["name"]
    )
    # the domain removed from the action is not removed from the record
    env.ref("hr.hr_employee_public_action").domain = False

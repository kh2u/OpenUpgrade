# Copyright Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# v19 employee_type selection value -> v20 hr.employee.type record
# TODO: worker, contractor and freelance have no v20 counterpart in data
_employee_type_xmlids = {
    "employee": "hr.contract_type_employee",
    "student": "hr.contract_type_student",
    "trainee": "hr.contract_type_intern",
}


@openupgrade.migrate()
def migrate(env, version):
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
    # types without v20 counterpart are removed with their xmlid
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
    for value, xmlid in _employee_type_xmlids.items():
        employee_type = env.ref(xmlid, raise_if_not_found=False)
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

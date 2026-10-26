# Copyright Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_models = [("hr.contract.type", "hr.employee.type")]

_renamed_tables = [("hr_contract_type", "hr_employee_type")]

_renamed_fields = [
    ("hr.job", "hr_job", "contract_type_id", "employee_type_id"),
    ("hr.version", "hr_version", "contract_type_id", "employee_type_id"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _renamed_models)
    openupgrade.rename_tables(env.cr, _renamed_tables)
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, [("hr.version", "fixed_term", "boolean", False)])

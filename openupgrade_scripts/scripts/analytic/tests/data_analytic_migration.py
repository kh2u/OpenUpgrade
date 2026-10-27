from odoo.tools import sql

env = locals().get("env")

# distribution model without distribution (required in 20.0)
env["account.analytic.distribution.model"].create(
    {"company_id": False, "sequence": 4242}
)

# plan column as created by older versions: `set null` on delete
plan = env["account.analytic.plan"].create({"name": "OU Analytic Test Plan"})
column = plan._strict_column_name()
env.cr.execute(
    """
    UPDATE ir_model_fields SET on_delete = 'set null'
    WHERE model = 'account.analytic.line' AND name = %s
    """,
    (column,),
)
constraint = f"account_analytic_line_{column}_fkey"
sql.drop_constraint(env.cr, "account_analytic_line", constraint)
sql.add_foreign_key(
    env.cr,
    "account_analytic_line",
    column,
    "account_analytic_account",
    "id",
    "set null",
)

env.cr.commit()

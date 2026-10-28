# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
env = locals().get("env")

for layout in ("striped", "boxed", "bold", "bubble", "folder", "wave"):
    env["res.company"].create(
        {
            "name": f"Web {layout} layout company",
            "external_report_layout_id": env.ref(f"web.external_layout_{layout}").id,
        }
    )

env.cr.commit()

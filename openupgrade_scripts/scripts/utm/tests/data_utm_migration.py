env = locals().get("env")

# records without xmlid whose name is the one of a new 20.0 data record
env["utm.source"].create({"name": "Google"})
env["utm.medium"].create({"name": "Social Media"})

env.cr.commit()

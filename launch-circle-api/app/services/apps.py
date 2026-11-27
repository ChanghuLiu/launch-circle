"""Shared App mutation rules used by owners and support tooling."""


def apply_app_update(app, body):
    values = body.model_dump(exclude_unset=True)
    for name, value in values.items():
        if name == "core_workflow_steps" and value is None:
            continue
        if name in {"opt_in_url", "google_group_url"} and value is not None:
            value = str(value)
        setattr(app, name, value)
    return app

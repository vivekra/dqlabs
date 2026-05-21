# DigitalQ Labs — Celery Task Autodiscovery
from apps.orchestrator.tasks.provision import provision_workspace  # noqa: F401
from apps.orchestrator.tasks.suspend import suspend_workspace  # noqa: F401
from apps.orchestrator.tasks.terminate import terminate_workspace  # noqa: F401
from apps.orchestrator.tasks.idle_monitor import detect_idle_workspaces  # noqa: F401

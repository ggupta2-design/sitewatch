"""Safe, bounded website health checks."""

from .checks import CheckRun, evaluate_observation, run_checks
from .config import config_from_dict, load_config, target_from_dict
from .http import observe_target
from .models import CheckResult, CheckState, Observation, Target
from .output import write_output
from .report import check_run_to_dict, format_check_run
from .safety import (
    SiteWatchError,
    validate_http_url,
    validate_public_resolution,
)

__version__ = "0.1.0"

__all__ = [
    "CheckResult",
    "CheckRun",
    "CheckState",
    "Observation",
    "SiteWatchError",
    "Target",
    "check_run_to_dict",
    "config_from_dict",
    "evaluate_observation",
    "format_check_run",
    "load_config",
    "observe_target",
    "run_checks",
    "target_from_dict",
    "validate_http_url",
    "validate_public_resolution",
    "write_output",
    "__version__",
]

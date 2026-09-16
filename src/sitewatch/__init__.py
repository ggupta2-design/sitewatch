"""Safe, bounded website health checks and change detection."""

from .baseline import (
    Baseline,
    BaselineEntry,
    baseline_from_dict,
    baseline_from_run,
    baseline_to_dict,
    format_baseline,
    load_baseline,
)
from .checks import CheckRun, evaluate_observation, run_checks
from .config import config_from_dict, load_config, target_from_dict
from .drift import DriftResult, DriftRun, DriftState, compare_to_baseline
from .drift_report import drift_run_to_dict, format_drift_run
from .http import observe_target
from .link_http import check_link_destination, fetch_html_page
from .link_report import format_link_audit, link_audit_to_dict
from .links import (
    HtmlPage,
    LinkAudit,
    LinkAuditPolicy,
    LinkDiscovery,
    LinkResult,
    LinkState,
    audit_links,
    discover_links,
)
from .models import CheckResult, CheckState, Observation, Target
from .output import write_output
from .report import check_run_to_dict, format_check_run
from .safety import (
    SiteWatchError,
    validate_http_url,
    validate_public_resolution,
)

__version__ = "0.3.0"

__all__ = [
    "Baseline",
    "BaselineEntry",
    "CheckResult",
    "CheckRun",
    "CheckState",
    "DriftResult",
    "DriftRun",
    "DriftState",
    "HtmlPage",
    "LinkAudit",
    "LinkAuditPolicy",
    "LinkDiscovery",
    "LinkResult",
    "LinkState",
    "Observation",
    "SiteWatchError",
    "Target",
    "baseline_from_dict",
    "baseline_from_run",
    "baseline_to_dict",
    "audit_links",
    "check_link_destination",
    "check_run_to_dict",
    "compare_to_baseline",
    "config_from_dict",
    "discover_links",
    "drift_run_to_dict",
    "evaluate_observation",
    "fetch_html_page",
    "format_baseline",
    "format_check_run",
    "format_drift_run",
    "format_link_audit",
    "link_audit_to_dict",
    "load_baseline",
    "load_config",
    "observe_target",
    "run_checks",
    "target_from_dict",
    "validate_http_url",
    "validate_public_resolution",
    "write_output",
    "__version__",
]

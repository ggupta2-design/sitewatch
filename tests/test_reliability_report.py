import json

from sitewatch.reliability import AlertDecision, ReliabilityCheck
from sitewatch.reliability_report import (
    alert_decision_to_dict,
    format_alert_decision,
)


def decision(alert=True):
    checks = (
        ReliabilityCheck(
            code="availability_below_minimum",
            observed=98.5,
            limit=99.0,
            passed=not alert,
        ),
        ReliabilityCheck(
            code="errors_exceeded",
            observed=0,
            limit=1,
            passed=True,
        ),
    )
    return AlertDecision(
        policy_name="production",
        checks=checks,
        samples=20,
        targets=2,
    )


def test_decision_dictionary_contains_aggregate_checks():
    payload = alert_decision_to_dict(decision())

    assert payload["alert"]
    assert payload["policy"] == "production"
    assert payload["summary"] == {
        "targets": 2,
        "samples": 20,
        "checks": 2,
        "failed_checks": 1,
    }
    assert payload["finding_codes"] == ["availability_below_minimum"]


def test_json_report_is_deterministic_and_value_limited():
    report = format_alert_decision(decision(), as_json=True)
    payload = json.loads(report)

    assert payload["checks"][0]["observed"] == 98.5
    assert report.endswith("\n")
    assert "https://" not in report
    assert "network_error" not in report
    assert '"name"' not in report
    assert '"status"' not in report


def test_text_report_explains_clear_and_alert_decisions():
    alert_report = format_alert_decision(decision())
    clear_report = format_alert_decision(decision(alert=False))

    assert "Decision: alert" in alert_report
    assert "availability_below_minimum: failed" in alert_report
    assert "observed 98.5, limit 99" in alert_report
    assert "Decision: clear" in clear_report
    assert "Failed checks: 0" in clear_report

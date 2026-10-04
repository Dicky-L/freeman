from .models import IndustrialEvent, RuleDecision, Severity

THRESHOLDS: dict[str, tuple[float, float, float]] = {
    "energy_deviation_pct": (10.0, 20.0, 35.0),
    "temperature_c": (60.0, 75.0, 90.0),
    "vibration_mm_s": (4.5, 7.1, 11.2),
}


def evaluate_rules(event: IndustrialEvent) -> RuleDecision:
    thresholds = THRESHOLDS.get(event.metric)
    if thresholds is None:
        return RuleDecision(
            severity=Severity.INFO,
            reason_codes=["NO_RULE"],
            requires_ai_enrichment=False,
            requires_workflow_task=False,
        )

    warning, high, critical = thresholds
    value = abs(event.value)
    if value >= critical:
        severity, reason = Severity.CRITICAL, "THRESHOLD_CRITICAL"
    elif value >= high:
        severity, reason = Severity.HIGH, "THRESHOLD_HIGH"
    elif value >= warning:
        severity, reason = Severity.WARNING, "THRESHOLD_WARNING"
    else:
        severity, reason = Severity.INFO, "WITHIN_RANGE"

    return RuleDecision(
        severity=severity,
        reason_codes=[reason],
        requires_ai_enrichment=severity in {Severity.WARNING, Severity.HIGH, Severity.CRITICAL},
        requires_workflow_task=severity in {Severity.HIGH, Severity.CRITICAL},
    )

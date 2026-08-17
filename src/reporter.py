"""Generate fix summary reports after incident resolution."""

from __future__ import annotations

from datetime import datetime, timezone

from src.db import get_incident, get_tool_timings, list_events, list_runs
from src.logger import get_logger

logger = get_logger(__name__)


def _format_duration(start: str, end: str | None) -> str:
    """Format duration between two ISO timestamps."""
    if not end:
        return "in progress"
    try:
        t1 = datetime.fromisoformat(start)
        t2 = datetime.fromisoformat(end)
        delta = t2 - t1
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}m {seconds}s"
    except (ValueError, TypeError):
        return "unknown"


def _tool_performance_stats(timings: list[dict]) -> dict:
    """Compute per-tool performance statistics."""
    stats: dict[str, dict] = {}
    for t in timings:
        name = t["tool_name"]
        if name not in stats:
            stats[name] = {"count": 0, "total_ms": 0, "success": 0, "failure": 0}
        stats[name]["count"] += 1
        stats[name]["total_ms"] += t["duration_ms"]
        if t["success"]:
            stats[name]["success"] += 1
        else:
            stats[name]["failure"] += 1
    for name, s in stats.items():
        s["avg_ms"] = s["total_ms"] // s["count"] if s["count"] > 0 else 0
    return stats


def generate_report(db_path: str, incident_id: str) -> dict:
    """Generate a full incident report with markdown + JSON output.

    Returns: {"markdown": str, "json": dict}
    """
    incident = get_incident(db_path, incident_id)
    if not incident:
        logger.warning("report_incident_not_found", incident_id=incident_id)
        return {"markdown": f"# Error\nIncident {incident_id} not found", "json": {}}

    runs = list_runs(db_path, incident_id)
    all_events: list[dict] = []
    all_timings: list[dict] = []

    for run in runs:
        events = list_events(db_path, run["id"])
        timings = get_tool_timings(db_path, run["id"])
        all_events.extend(events)
        all_timings.extend(timings)

    # Build JSON report
    latest_run = runs[-1] if runs else None
    tool_stats = _tool_performance_stats(all_timings)

    report_json = {
        "incident": {
            "id": incident["id"],
            "title": incident["title"],
            "description": incident["description"],
            "container_name": incident.get("container_name"),
            "status": incident["status"],
            "severity": incident["severity"],
            "created_at": incident["created_at"],
            "resolved_at": incident.get("resolved_at"),
            "duration": _format_duration(
                incident["created_at"], incident.get("resolved_at")
            ),
        },
        "runs": [
            {
                "id": r["id"],
                "run_number": r["run_number"],
                "status": r["status"],
                "started_at": r["started_at"],
                "completed_at": r.get("completed_at"),
                "duration": _format_duration(r["started_at"], r.get("completed_at")),
                "rca_result": r.get("rca_result"),
                "plan_result": r.get("plan_result"),
                "execution_result": r.get("execution_result"),
                "validation_result": r.get("validation_result"),
            }
            for r in runs
        ],
        "total_events": len(all_events),
        "tool_performance": tool_stats,
    }

    # Build Markdown report
    inc = report_json["incident"]
    lines = [
        f"# Incident Report: {inc['title']}",
        "",
        f"**Status:** {inc['status']}  ",
        f"**Severity:** {inc['severity']}  ",
        f"**Container:** {inc.get('container_name') or 'N/A'}  ",
        f"**Created:** {inc['created_at']}  ",
        f"**Resolved:** {inc.get('resolved_at') or 'Not yet resolved'}  ",
        f"**Duration:** {inc['duration']}",
        "",
    ]

    if latest_run:
        # RCA section
        rca = latest_run.get("rca_result") or {}
        if rca:
            lines += [
                "## Root Cause Analysis",
                "",
                f"**Root Cause:** {rca.get('root_cause', 'Unknown')}",
                f"**Category:** {rca.get('category', 'unknown')}",
                f"**Confidence:** {float(rca.get('confidence', 0) or 0):.0%}",
                "",
                f"**Details:** {rca.get('details', '')}",
                "",
            ]
            evidence = rca.get("evidence", [])
            if evidence:
                lines.append("**Evidence:**")
                for e in evidence:
                    lines.append(f"- {e}")
                lines.append("")

        # Plan section
        plan = latest_run.get("plan_result") or {}
        if plan:
            steps = plan.get("steps", [])
            lines += [
                "## Remediation Plan",
                "",
                f"**Strategy:** {plan.get('overall_strategy', '')}",
                f"**Risk:** {plan.get('estimated_risk', 'unknown')}",
                f"**Requires Downtime:** {plan.get('requires_downtime', False)}",
                "",
                "### Steps",
                "",
            ]
            for step in steps:
                lines.append(
                    f"{step.get('step_number', '?')}. {step.get('action', '')}"
                )
                if step.get("expected_outcome"):
                    lines.append(f"   - *Expected:* {step['expected_outcome']}")
            lines.append("")

        # Execution section
        execution = latest_run.get("execution_result") or {}
        if execution:
            lines += [
                "## Execution",
                "",
                f"**Overall Success:** {execution.get('overall_success', False)}",
                f"**Container Status After:** {execution.get('container_status_after', 'unknown')}",
                "",
            ]
            executed_steps = execution.get("executed_steps", [])
            if executed_steps:
                lines.append("| Step | Action | Tool | Success |")
                lines.append("|------|--------|------|---------|")
                for s in executed_steps:
                    lines.append(
                        f"| {s.get('step_number', '?')} | {s.get('action_taken', '')} | "
                        f"{s.get('tool_used', '')} | {'yes' if s.get('success') else 'no'} |"
                    )
                lines.append("")

        # Validation section
        validation = latest_run.get("validation_result") or {}
        if validation:
            validated = validation.get("validated", False)
            lines += [
                "## Validation",
                "",
                f"**Validated:** {'Yes' if validated else 'No'}",
                f"**Container Status:** {validation.get('container_status', 'unknown')}",
                f"**Confidence:** {float(validation.get('confidence', 0) or 0):.0%}",
                "",
            ]
            checks = validation.get("checks", [])
            if checks:
                lines.append("| Check | Result | Passed |")
                lines.append("|-------|--------|--------|")
                for c in checks:
                    lines.append(
                        f"| {c.get('check', '')} | {c.get('result', '')} | "
                        f"{'yes' if c.get('passed') else 'no'} |"
                    )
                lines.append("")

    # Timeline
    if len(runs) > 1:
        lines += [
            f"## Run History ({len(runs)} attempts)",
            "",
            "| Run | Status | Duration |",
            "|-----|--------|----------|",
        ]
        for r in runs:
            lines.append(
                f"| {r['run_number']} | {r['status']} | "
                f"{_format_duration(r['started_at'], r.get('completed_at'))} |"
            )
        lines.append("")

    # Tool performance
    if tool_stats:
        lines += [
            "## Tool Performance",
            "",
            "| Tool | Calls | Avg (ms) | Success | Failure |",
            "|------|-------|----------|---------|---------|",
        ]
        for tool_name, s in sorted(tool_stats.items()):
            lines.append(
                f"| {tool_name} | {s['count']} | {s['avg_ms']} | {s['success']} | {s['failure']} |"
            )
        lines.append("")

    lines += [
        "---",
        f"*Report generated at {datetime.now(timezone.utc).isoformat()}*",
    ]

    return {
        "markdown": "\n".join(lines),
        "json": report_json,
    }

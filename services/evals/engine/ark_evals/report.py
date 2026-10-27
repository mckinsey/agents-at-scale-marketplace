"""Render a run report as Markdown (story 04) with a threshold verdict (story 05).

The report is the only signal in Milestone 1: it states the threshold, the pass
rate, a PASS / BELOW-THRESHOLD verdict, and a per-case account of what was
evaluated and what passed. It does not act (report-only).
"""

from __future__ import annotations

from .schemas import CheckType, RunReport

_VERDICT_PASS = "✅ PASS"
_VERDICT_BELOW = "❌ BELOW-THRESHOLD"


def render_markdown(report: RunReport) -> str:
    """Return the full Markdown report for a run."""
    pct = report.pass_rate * 100
    thr = report.threshold * 100
    verdict = _VERDICT_BELOW if report.below_threshold else _VERDICT_PASS

    lines: list[str] = []
    lines.append(f"# Eval report — {report.suite}")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict}")
    lines.append(f"- **Pass rate:** {pct:.0f}% ({report.passed}/{report.passed + report.failed} evaluated)")
    lines.append(f"- **Threshold:** {thr:.0f}%")
    lines.append(f"- **Judge model:** `{report.judge_model}`")
    lines.append(f"- **Output evaluated:** `{report.output_path}`")
    if report.workflow:
        lines.append(f"- **Workflow run:** `{report.workflow}`")
    if report.errored:
        lines.append(
            f"- **Could not evaluate:** {report.errored} case(s) — see the errors "
            f"table below (an eval error is not an output failure)"
        )
    lines.append("")

    lines.append("## Cases")
    lines.append("")
    lines.append("| Case | Check | Slice | Result | Detail |")
    lines.append("|------|-------|-------|--------|--------|")
    for r in report.results:
        if r.error is not None:
            status = "⚠️ error"
            detail = r.error
        elif r.passed:
            status = "pass"
            detail = r.detail
        else:
            status = "fail"
            detail = r.detail
        lines.append(
            f"| `{r.case_id}` | {r.check.value} | `{r.slice}` | {status} | {_cell(detail)} |"
        )
    lines.append("")

    judged = [r for r in report.results if r.check is CheckType.JUDGE and r.verdict]
    if judged:
        lines.append("## Judge rationale")
        lines.append("")
        for r in judged:
            lines.append(f"### `{r.case_id}`")
            scores = ", ".join(f"{d}={s}" for d, s in r.verdict.dimension_scores.items())
            lines.append(f"- Scores: {scores or '(none)'}")
            for dim, why in r.verdict.rationale.items():
                lines.append(f"- **{dim}**: {why}")
            if r.verdict.improvement_suggestions:
                lines.append("- Suggestions: " + "; ".join(r.verdict.improvement_suggestions))
            lines.append("")

    return "\n".join(lines) + "\n"


def render_summary_line(report: RunReport) -> str:
    """One-line summary echoed to the handler log."""
    verdict = "BELOW-THRESHOLD" if report.below_threshold else "PASS"
    pct = report.pass_rate * 100
    extra = f", {report.errored} errored" if report.errored else ""
    return (
        f"[eval:{report.suite}] {verdict} — {pct:.0f}% "
        f"({report.passed}/{report.passed + report.failed}{extra}), "
        f"threshold {report.threshold * 100:.0f}%"
    )


def _cell(text: str) -> str:
    """Make a string safe for a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")

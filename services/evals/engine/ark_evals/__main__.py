"""CLI entrypoint for the eval engine.

Two commands:

- ``run``      : evaluate a produced output against a suite and write a report.
- ``validate`` : check a suite on disk is well-formed, without running anything
                 (story 06: a doctor-style pre-run check).

``run`` is what the Argo ``onExit`` handler invokes. It always writes a Markdown
report and echoes a one-line summary. Report-only: a below-threshold result is
reported, never enforced (exits 0), so it does not fail the workflow run
(story 02/05).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ark_query import ask_model
from .grader import grade_suite
from .output_source import OutputError, load_input, load_output
from .report import render_markdown, render_summary_line
from .suite_loader import SuiteError, load_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ark-evals", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="evaluate a produced output against a suite")
    p_run.add_argument("--suite-dir", required=True, help="mounted suite ConfigMap dir")
    p_run.add_argument("--output-key", required=True, help="file-gateway key of the produced output")
    p_run.add_argument("--input-key", default="", help="file-gateway key of the workflow input (optional; enables source:input cases and judge grounding)")
    p_run.add_argument("--report-key", required=True, help="file-gateway key to write the Markdown report to")
    p_run.add_argument("--file-gateway-url", required=True, help="file-gateway REST base URL")
    p_run.add_argument("--namespace", default="default", help="namespace for judge Queries")
    p_run.add_argument("--workflow", default="", help="workflow run name, for the report header")

    p_val = sub.add_parser("validate", help="check a suite is well-formed (no run)")
    p_val.add_argument("--suite-dir", required=True, help="mounted suite ConfigMap dir")

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _cmd_validate(args)
    return _cmd_run(args)


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        suite = load_suite(args.suite_dir)
    except SuiteError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    judges = ", ".join(sorted(suite.judges)) or "none"
    print(
        f"OK: suite {suite.name!r} — {len(suite.cases)} cases, judges: {judges}, "
        f"judge model {suite.judge_model!r}, threshold {suite.threshold:.0%}"
    )
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    # A malformed suite or unreadable output is a configuration/eval error
    # (story 01/03): report it clearly and exit non-zero — this is the one case
    # that is NOT "report-only", because there was nothing to evaluate.
    try:
        suite = load_suite(args.suite_dir)
    except SuiteError as exc:
        print(f"eval configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        output = load_output(args.file_gateway_url, args.output_key)
    except OutputError as exc:
        print(f"eval could not read output: {exc}", file=sys.stderr)
        return 2

    # The workflow input is optional. If given, cases can target source:input
    # and the judge scores faithfulness against the real input. A missing input
    # file is an eval error only for cases that need it, not for the whole run.
    workflow_input = None
    if args.input_key:
        try:
            workflow_input = load_input(args.file_gateway_url, args.input_key)
        except OutputError as exc:
            print(f"warning: could not read input {args.input_key!r}: {exc}", file=sys.stderr)

    def judge_caller(prompt: str, model: str) -> str:
        return ask_model(prompt, model=model, namespace=args.namespace)

    report = grade_suite(
        suite,
        output,
        output_path=args.output_key,
        workflow=args.workflow,
        judge_caller=judge_caller,
        workflow_input=workflow_input,
    )

    markdown = render_markdown(report)
    _write_report(args.file_gateway_url, args.report_key, markdown)

    # Echo the summary to the handler log (story 04/05). Report-only: exit 0
    # even below threshold, so the eval never fails the workflow run.
    print(render_summary_line(report))
    print(f"report written to {args.report_key}")
    return 0


def _write_report(base_url: str, key: str, markdown: str) -> None:
    """Upload the Markdown report to the file-gateway via POST /files.

    file-gateway ``POST /files`` is a multipart upload: a ``file`` part plus a
    ``prefix`` form field, and the stored key is ``prefix + filename``. We split
    the report key into its directory prefix and filename to reconstruct the
    exact key. Built with stdlib only (no requests/httpx) to keep the image lean.
    """
    from posixpath import basename, dirname
    from urllib.request import Request, urlopen

    filename = basename(key)
    prefix = dirname(key)
    prefix = (prefix + "/") if prefix else ""

    boundary = "----ark-evals-report-boundary"
    body = _multipart_body(boundary, filename, prefix, markdown)
    req = Request(
        f"{base_url.rstrip('/')}/files",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:  # noqa: S310 — in-cluster URL
            if resp.status not in (200, 201):
                print(f"warning: report upload returned HTTP {resp.status}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — never fail the run on report upload
        print(f"warning: could not upload report to {key}: {exc}", file=sys.stderr)
        # Fall back to stdout so the report is never lost.
        print("----- BEGIN EVAL REPORT -----")
        print(markdown)
        print("----- END EVAL REPORT -----")


def _multipart_body(boundary: str, filename: str, prefix: str, content: str) -> bytes:
    """Build a minimal multipart/form-data body: a file part + a prefix field."""
    crlf = "\r\n"
    parts = [
        f"--{boundary}",
        f'Content-Disposition: form-data; name="file"; filename="{filename}"',
        "Content-Type: text/markdown",
        "",
        content,
        f"--{boundary}",
        'Content-Disposition: form-data; name="prefix"',
        "",
        prefix,
        f"--{boundary}--",
        "",
    ]
    return crlf.join(parts).encode("utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

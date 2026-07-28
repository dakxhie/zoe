"""Pytest coverage for the system doctor."""

from __future__ import annotations

from unittest.mock import patch

from core.doctor import (
    CheckResult,
    CheckStatus,
    CollectionInfo,
    DoctorReport,
    check_configuration,
    check_python,
    print_doctor_report,
    run_doctor,
)


def test_check_python_passes_on_supported_version() -> None:
    """Report PASS when Python meets the minimum version."""
    with patch("core.doctor.sys.version_info", (3, 12, 0)):
        result = check_python()

    assert result.status == CheckStatus.PASS
    assert "Python 3.12.0" in result.details[0]


def test_check_configuration_reports_missing_keys() -> None:
    """Report FAIL when required settings keys are absent."""
    with patch("core.doctor.load_settings", return_value={"MODEL_NAME": "test-model"}):
        result = check_configuration()

    assert result.status == CheckStatus.FAIL
    assert any("Missing keys" in detail for detail in result.details)


def test_run_doctor_never_raises_and_returns_report() -> None:
    """Return a structured report even when individual checks fail."""
    failing = CheckResult("Dependencies", CheckStatus.FAIL, details=["torch missing"])

    with patch("core.doctor.check_python", return_value=CheckResult("Python", CheckStatus.PASS)), patch(
        "core.doctor.check_dependencies",
        return_value=failing,
    ), patch(
        "core.doctor.check_configuration",
        return_value=CheckResult("Configuration", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_folders",
        return_value=CheckResult("Folders", CheckStatus.WARN),
    ), patch(
        "core.doctor.check_chroma",
        return_value=(
            CheckResult("Chroma", CheckStatus.PASS),
            [CollectionInfo("zoe_notes", 0, "docs")],
        ),
    ), patch(
        "core.doctor.check_memory",
        return_value=CheckResult("Memory", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_notes",
        return_value=CheckResult("Notes", CheckStatus.WARN, details=["No notes indexed."]),
    ), patch(
        "core.doctor.check_pdf",
        return_value=CheckResult("PDF", CheckStatus.WARN, details=["No PDFs indexed."]),
    ), patch(
        "core.doctor.check_code",
        return_value=CheckResult("Code", CheckStatus.WARN, details=["No code indexed."]),
    ), patch(
        "core.doctor.check_web",
        return_value=CheckResult("Web", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_vision",
        return_value=CheckResult("Vision", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_agents",
        return_value=CheckResult("Agents", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_tools",
        return_value=CheckResult("Tools", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_cli",
        return_value=CheckResult("CLI", CheckStatus.PASS, details=["Commands: chat, doctor"]),
    ), patch(
        "core.doctor.check_model",
        return_value=CheckResult("Model", CheckStatus.PASS),
    ), patch(
        "core.doctor.check_runtime",
        return_value=(CheckResult("Runtime", CheckStatus.PASS), {"CPU": "test"}),
    ):
        report = run_doctor()

    assert isinstance(report, DoctorReport)
    assert report.overall_status == CheckStatus.FAIL
    assert len(report.checks) == 16
    assert report.recommended_fixes


def test_print_doctor_report_never_raises(capsys) -> None:
    """Print a readable report without raising."""
    report = DoctorReport(
        checks=[CheckResult("Python", CheckStatus.PASS)],
        collections=[CollectionInfo("zoe_memory", 2, "docs")],
        runtime={"CPU": "test"},
        overall_status=CheckStatus.PASS,
    )

    print_doctor_report(report)
    output = capsys.readouterr().out

    assert "ZOE SYSTEM DOCTOR" in output
    assert "HEALTHY" in output
    assert "zoe_memory" in output

"""Production deployment infrastructure for Zoe AI v2."""

from deployment.benchmark import BenchmarkReport, run_benchmark_suite
from deployment.config import ZoeConfig, get_config, load_config, reset_config_for_tests
from deployment.diagnostics import DeploymentDiagnostics, run_deployment_diagnostics
from deployment.environment import DeploymentProfile, RuntimeMode, detect_environment
from deployment.health import HealthStatus, run_health_checks
from deployment.resource_monitor import ResourceSnapshot, capture_resource_snapshot
from deployment.shutdown import run_shutdown_sequence
from deployment.startup import StartupReport, run_startup_sequence
from deployment.telemetry import record_telemetry, telemetry_enabled

__all__ = [
    "BenchmarkReport",
    "DeploymentDiagnostics",
    "DeploymentProfile",
    "HealthStatus",
    "ResourceSnapshot",
    "RuntimeMode",
    "StartupReport",
    "ZoeConfig",
    "capture_resource_snapshot",
    "detect_environment",
    "get_config",
    "load_config",
    "record_telemetry",
    "reset_config_for_tests",
    "run_benchmark_suite",
    "run_deployment_diagnostics",
    "run_health_checks",
    "run_shutdown_sequence",
    "run_startup_sequence",
    "telemetry_enabled",
]

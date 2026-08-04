"""Contract tests for the generated AgentScope release gate."""

import subprocess
from pathlib import Path

import pytest

from scripts.agentscope_release_gate import (
    REQUIRED_TEST_COMMANDS,
    SUPPORTED_PYTHON_VERSIONS,
    production_baseline,
    run_docker_journey,
    run_release_gate,
)


def test_production_baseline_enables_every_release_boundary() -> None:
    config = production_baseline()

    assert config.ai_framework.value == "agentscope"
    assert config.database.value == "postgresql"
    assert config.enable_redis and config.enable_docker
    assert config.enable_teams and config.enable_billing and config.enable_credits_system
    assert config.tenancy.value == "multi_org"
    assert config.rag_features.vector_store.value == "qdrant"
    assert config.frontend.value == "nextjs"


def test_release_gate_declares_supported_python_and_boundary_commands() -> None:
    assert SUPPORTED_PYTHON_VERSIONS == ("3.11", "3.12", "3.13")
    assert set(REQUIRED_TEST_COMMANDS) == {
        "backend_unit",
        "backend_integration",
        "backend_all",
        "backend_coverage",
        "frontend_lint",
        "frontend_typecheck",
        "frontend_unit",
        "frontend_e2e",
    }
    assert "-m 'not integration'" in REQUIRED_TEST_COMMANDS["backend_unit"]
    assert "--cov-branch" in REQUIRED_TEST_COMMANDS["backend_coverage"]


@pytest.mark.slow
def test_generated_production_baseline_passes_static_release_gate() -> None:
    report = run_release_gate(matrix=False)

    assert report.quality_gate_passed
    assert report.failed == 0
    assert report.generated_projects == ("Python 3.12",)
    assert report.pass_rate == 1.0


def test_docker_gate_skips_when_daemon_is_not_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("scripts.agentscope_release_gate.shutil.which", lambda _: None)

    result = run_docker_journey(tmp_path)

    assert result.status == "skip"
    assert "not installed" in result.detail


def test_docker_gate_materializes_ephemeral_env_before_compose(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Compose validation must work from the secret-free generated template."""

    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".env.example").write_text("POSTGRES_USER=postgres\n", encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr("scripts.agentscope_release_gate.shutil.which", lambda _: "/usr/bin/docker")

    def fake_run(
        command: list[str], *, cwd: Path, timeout: int = 300
    ) -> subprocess.CompletedProcess[str]:
        del cwd, timeout
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("scripts.agentscope_release_gate._run", fake_run)

    result = run_docker_journey(tmp_path)

    assert result.status == "pass"
    assert (backend / ".env").read_text(encoding="utf-8") == "POSTGRES_USER=postgres\n"
    assert any(command[-2:] == ["config", "--quiet"] for command in commands)

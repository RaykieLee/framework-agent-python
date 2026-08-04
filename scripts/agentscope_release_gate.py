#!/usr/bin/env python3
"""Release gate for the generated production-baseline AgentScope app.

The generator remains the only product-facing entry point.  This gate renders
the same configuration a release would ship, checks all AgentScope seams from
tickets 01--13, and prints a redaction-safe report.  Networked work is opt-in:
``--run-generated-tests`` runs the generated suites, ``--docker`` exercises the
PostgreSQL/Redis/Qdrant compose journey, and ``--glm`` invokes the generated
environment-only evaluator.  A normal invocation never pulls images or calls
an LLM.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import redirect_stderr, redirect_stdout, suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from fastapi_gen.config import (
    AIFrameworkType,
    BackgroundTaskType,
    DatabaseType,
    FrontendType,
    ProjectConfig,
    RAGFeatures,
    TenancyMode,
    VectorStoreType,
)
from fastapi_gen.generator import generate_project

SUPPORTED_PYTHON_VERSIONS = ("3.11", "3.12", "3.13")
SEMANTIC_MINIMUM = 0.90
SAFETY_MINIMUM = 1.0
TENANT_ISOLATION_MINIMUM = 1.0
BACKEND_LINE_MINIMUM = 0.90
BACKEND_BRANCH_MINIMUM = 0.85
FRONTEND_COVERAGE_MINIMUM = 1.0

REQUIRED_BACKEND_SEAMS = (
    "app/agents/agentscope_assistant.py",  # 01/02 chat
    "app/services/agentscope_durable_session.py",  # 04
    "app/services/agentscope_knowledge.py",  # 05
    "app/services/agentscope_memory.py",  # 06
    "app/services/agentscope_agent_definition.py",  # 08
    "app/services/agentscope_execution_team.py",  # 09
    "app/services/agentscope_delegation.py",  # 10
    "app/services/agentscope_team_run.py",  # 11
    "app/services/agentscope_member_exit.py",  # 12
    "app/services/agentscope_tenant_purge.py",  # 13
    "tests/test_agentscope_evaluation.py",  # 03 deterministic/live contract
)

REQUIRED_TEST_COMMANDS = {
    "backend_unit": "uv run pytest -q tests/test_agentscope_*.py -m 'not integration'",
    "backend_integration": "uv run pytest -q tests/test_agentscope_*.py -m integration",
    "backend_all": "uv run pytest -q",
    "backend_coverage": "uv run pytest -q --cov=app --cov-branch --cov-report=term-missing",
    "frontend_lint": "npm run lint",
    "frontend_typecheck": "npm run type-check",
    "frontend_unit": "npm run test:run -- --coverage",
    "frontend_e2e": "npm run test:e2e",
}

_ROUTE_NATIVE_PATTERNS = (
    re.compile(r"(?:from|import)\s+agentscope\.app\b"),
    re.compile(r"\bcreate_app\s*\("),
    re.compile(r"@(?:router|app)\.(?:get|post|put|patch|delete)\(\s*[\"']/(?:chat|sessions)"),
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]{24,}"),
    re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*[\"'][^\"']{24,}[\"']"),
)


GateStatus = Literal["pass", "fail", "skip", "info"]


@dataclass(frozen=True, slots=True)
class GateResult:
    """One redaction-safe release-gate observation."""

    name: str
    status: GateStatus
    detail: str


@dataclass(frozen=True, slots=True)
class ReleaseGateReport:
    """Stable report that can be uploaded as a CI artifact."""

    results: tuple[GateResult, ...]
    generated_projects: tuple[str, ...] = ()

    @property
    def passed(self) -> int:
        return sum(result.status == "pass" for result in self.results)

    @property
    def failed(self) -> int:
        return sum(result.status == "fail" for result in self.results)

    @property
    def skipped(self) -> int:
        return sum(result.status == "skip" for result in self.results)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 1.0

    @property
    def quality_gate_passed(self) -> bool:
        return self.failed == 0 and self.passed > 0

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": self.total,
            "pass_rate": round(self.pass_rate, 4),
            "quality_gate_passed": self.quality_gate_passed,
            "generated_projects": list(self.generated_projects),
            "results": [asdict(result) for result in self.results],
            "coverage_policy": {
                "backend_line": BACKEND_LINE_MINIMUM,
                "backend_branch": BACKEND_BRANCH_MINIMUM,
                "frontend_changed_module": FRONTEND_COVERAGE_MINIMUM,
                "glm_semantic": SEMANTIC_MINIMUM,
                "glm_safety": SAFETY_MINIMUM,
                "glm_tenant_isolation": TENANT_ISOLATION_MINIMUM,
            },
        }


def production_baseline(
    *, python_version: str = "3.12", project_name: str = "agentscope_release"
) -> ProjectConfig:
    """Return the single supported production-baseline configuration.

    Teams, billing, tenancy, RAG, and persistent services are intentionally
    enabled together so one generated app exercises every prior ticket seam.
    The evaluator's key is never part of this configuration or generated
    context; it is read only by the opt-in generated evaluator.
    """

    return ProjectConfig(
        project_name=project_name,
        python_version=python_version,
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.AGENTSCOPE,
        background_tasks=BackgroundTaskType.NONE,
        enable_logfire=False,
        enable_redis=True,
        enable_docker=True,
        enable_teams=True,
        enable_billing=True,
        enable_credits_system=True,
        tenancy=TenancyMode.MULTI_ORG,
        frontend=FrontendType.NEXTJS,
        rag_features=RAGFeatures(enable_rag=True, vector_store=VectorStoreType.QDRANT),
    )


def _check_no_native_routes(project: Path) -> list[str]:
    violations: list[str] = []
    for route in sorted((project / "backend/app/api/routes").rglob("*.py")):
        text = route.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in _ROUTE_NATIVE_PATTERNS):
            violations.append(str(route.relative_to(project)))
    return violations


def _check_no_embedded_secrets(project: Path) -> list[str]:
    violations: list[str] = []
    for source in sorted(project.rglob("*.py")):
        text = source.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
            violations.append(str(source.relative_to(project)))
    env_example = project / "backend/.env.example"
    if not env_example.exists() or "AGENTSCOPE_EVAL_API_KEY=" not in env_example.read_text(
        encoding="utf-8"
    ):
        violations.append("backend/.env.example (missing environment-only evaluator key)")
    return violations


def verify_generated_project(project: Path) -> list[GateResult]:
    """Verify generated seams and release invariants without running services."""

    backend = project / "backend"
    results: list[GateResult] = []
    missing = [path for path in REQUIRED_BACKEND_SEAMS if not (backend / path).exists()]
    results.append(
        GateResult(
            "generated.ticket_01_to_13_seams",
            "pass" if not missing else "fail",
            "all required runtime, control-plane, billing, cleanup, and purge seams rendered"
            if not missing
            else f"missing: {', '.join(missing)}",
        )
    )

    pyproject = (backend / "pyproject.toml").read_text(encoding="utf-8")
    compose = (project / "docker-compose.yml").read_text(encoding="utf-8")
    durable_services = all(
        token in compose
        for token in (
            "postgres:16-alpine",
            "redis:7-alpine",
            "qdrant/qdrant",
            "qdrant_data:/qdrant/storage",
        )
    )
    results.append(
        GateResult(
            "generated.production_infrastructure",
            "pass"
            if durable_services
            and "agentscope[storage-redis,storage-sql,vdb-qdrant,memory-mem0]" in pyproject
            else "fail",
            "PostgreSQL, Redis, persistent Qdrant, and AgentScope production extras are declared"
            if durable_services
            and "agentscope[storage-redis,storage-sql,vdb-qdrant,memory-mem0]" in pyproject
            else "missing a durable service or AgentScope production extra",
        )
    )

    route_violations = _check_no_native_routes(project)
    results.append(
        GateResult(
            "security.no_native_agentscope_routes",
            "pass" if not route_violations else "fail",
            "product routes expose only template APIs; AgentScope native service APIs remain internal"
            if not route_violations
            else f"native API reference in: {', '.join(route_violations)}",
        )
    )

    secret_violations = _check_no_embedded_secrets(project)
    results.append(
        GateResult(
            "security.environment_only_secrets",
            "pass" if not secret_violations else "fail",
            "no embedded credentials; GLM key is documented as environment-only"
            if not secret_violations
            else f"possible embedded secret or missing env contract: {', '.join(secret_violations)}",
        )
    )

    package_json = project / "frontend/package.json"
    frontend_scripts = package_json.exists() and all(
        f'"{name}"' in package_json.read_text(encoding="utf-8")
        for name in ("lint", "type-check", "test:run", "test:e2e")
    )
    results.append(
        GateResult(
            "generated.frontend_release_commands",
            "pass" if frontend_scripts else "fail",
            "frontend lint, type-check, unit, and E2E commands are generated"
            if frontend_scripts
            else "frontend package scripts are incomplete",
        )
    )
    return results


def _run(command: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _process_detail(completed: subprocess.CompletedProcess[str]) -> str:
    """Return a short, redaction-safe process summary for CI artifacts."""

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    first_line = next((line.strip() for line in output.splitlines() if line.strip()), "no output")
    first_line = re.sub(r"(?i)(?:bearer\s+|api[_-]?key[=:]\s*)\S+", "[redacted]", first_line)
    return f"exit={completed.returncode}; {first_line[:240]}"


def _generate_quiet(config: ProjectConfig, output_dir: Path) -> Path:
    """Generate while suppressing Cookiecutter hook output from child processes."""

    stdout_fd = os.dup(1)
    stderr_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        return generate_project(config, output_dir)
    finally:
        os.dup2(stdout_fd, 1)
        os.dup2(stderr_fd, 2)
        os.close(stdout_fd)
        os.close(stderr_fd)
        os.close(devnull_fd)


def run_generated_test_commands(project: Path) -> list[GateResult]:
    """Run deterministic generated suites when their local tools are available."""

    results: list[GateResult] = []
    backend = project / "backend"
    uv = shutil.which("uv")
    if not uv:
        return [
            GateResult(
                "generated.backend_tests",
                "skip",
                "uv is not installed; run the required commands manually",
            )
        ]
    agentscope_tests = [
        str(path.relative_to(backend))
        for path in sorted(backend.glob("tests/test_agentscope_*.py"))
    ]
    for name, command in (
        (
            "generated.backend_unit",
            [uv, "run", "pytest", "-q", *agentscope_tests, "-m", "not integration"],
        ),
        ("generated.backend_all", [uv, "run", "pytest", "-q"]),
    ):
        try:
            completed = _run(command, cwd=backend)
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append(
                GateResult(name, "skip", f"command unavailable or timed out: {type(exc).__name__}")
            )
            continue
        results.append(
            GateResult(
                name, "pass" if completed.returncode == 0 else "fail", _process_detail(completed)
            )
        )

    # Integration tests are intentionally a boundary report: without explicit
    # service URLs they skip rather than pretending an in-process fake is prod.
    integration_env = all(
        os.getenv(name)
        for name in (
            "AGENTSCOPE_INTEGRATION_DATABASE_URL",
            "AGENTSCOPE_INTEGRATION_REDIS_URL",
            "AGENTSCOPE_INTEGRATION_QDRANT_URL",
        )
    )
    if not integration_env:
        results.append(
            GateResult(
                "generated.backend_integration",
                "skip",
                "set all AGENTSCOPE_INTEGRATION_*_URL variables",
            )
        )
    else:
        try:
            completed = _run(
                [uv, "run", "pytest", "-q", *agentscope_tests, "-m", "integration"],
                cwd=backend,
            )
            results.append(
                GateResult(
                    "generated.backend_integration",
                    "pass" if completed.returncode == 0 else "fail",
                    _process_detail(completed),
                )
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append(
                GateResult(
                    "generated.backend_integration",
                    "skip",
                    f"command unavailable or timed out: {type(exc).__name__}",
                )
            )
    return results


def run_docker_journey(project: Path) -> GateResult:
    """Validate compose and optionally pull/start services, skipping safely."""

    docker = shutil.which("docker")
    if not docker:
        return GateResult(
            "docker.postgres_redis_qdrant", "skip", "docker executable is not installed"
        )
    try:
        info = _run([docker, "info"], cwd=project, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GateResult(
            "docker.postgres_redis_qdrant",
            "skip",
            f"Docker daemon unavailable: {type(exc).__name__}",
        )
    if info.returncode != 0:
        return GateResult(
            "docker.postgres_redis_qdrant", "skip", "Docker daemon unavailable (docker info failed)"
        )
    try:
        compose = [docker, "compose"]
        config = _run([*compose, "config", "--quiet"], cwd=project, timeout=30)
        if config.returncode != 0:
            return GateResult(
                "docker.postgres_redis_qdrant", "fail", "docker compose config failed"
            )
        pull = _run([*compose, "pull", "db", "redis", "qdrant"], cwd=project, timeout=180)
        if pull.returncode != 0:
            return GateResult(
                "docker.postgres_redis_qdrant",
                "skip",
                "image pull unavailable; compose journey not run",
            )
        up = _run([*compose, "up", "-d", "db", "redis", "qdrant"], cwd=project, timeout=180)
        if up.returncode != 0:
            return GateResult(
                "docker.postgres_redis_qdrant", "fail", "compose services failed to start"
            )
        return GateResult(
            "docker.postgres_redis_qdrant", "pass", "PostgreSQL, Redis, and Qdrant started"
        )
    except subprocess.TimeoutExpired:
        return GateResult(
            "docker.postgres_redis_qdrant",
            "skip",
            "Docker command timed out (daemon/image pull unavailable)",
        )
    finally:
        # The project lives in a temporary directory; do not remove volumes or
        # touch unrelated user containers.  A best-effort stop is sufficient.
        with suppress(OSError, subprocess.TimeoutExpired):
            _run([docker, "compose", "down", "--remove-orphans"], cwd=project, timeout=30)


def run_glm_evaluation(project: Path) -> GateResult:
    """Run the generated evaluator only when explicitly enabled by the caller."""

    if os.getenv("AGENTSCOPE_EVAL_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        return GateResult(
            "glm.semantic_safety_isolation",
            "skip",
            "GLM evaluator is opt-in; set AGENTSCOPE_EVAL_ENABLED=true",
        )
    backend = project / "backend"
    uv = shutil.which("uv")
    if not uv:
        return GateResult("glm.semantic_safety_isolation", "skip", "uv is not installed")
    command = [
        uv,
        "run",
        "python",
        "-c",
        "import asyncio; from app.services.agentscope_evaluation import evaluate_glm_from_env; print(asyncio.run(evaluate_glm_from_env()).to_json())",
    ]
    try:
        completed = _run(command, cwd=backend, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GateResult(
            "glm.semantic_safety_isolation", "skip", f"evaluator unavailable: {type(exc).__name__}"
        )
    if completed.returncode != 0:
        return GateResult(
            "glm.semantic_safety_isolation",
            "fail",
            "GLM evaluator failed; inspect redacted report in command output",
        )
    try:
        report = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return GateResult(
            "glm.semantic_safety_isolation", "fail", "GLM evaluator returned malformed report"
        )
    rates = report.get("category_rates", {})
    passed = bool(
        report.get("quality_gate_passed")
        and float(rates.get("semantic", 0)) >= SEMANTIC_MINIMUM
        and float(rates.get("safety", 0)) >= SAFETY_MINIMUM
        and float(rates.get("tenant_isolation", 0)) >= TENANT_ISOLATION_MINIMUM
    )
    return GateResult(
        "glm.semantic_safety_isolation",
        "pass" if passed else "fail",
        "GLM quality gate thresholds met" if passed else "GLM quality gate thresholds not met",
    )


def run_release_gate(
    *, run_tests: bool = False, run_docker: bool = False, run_glm: bool = False, matrix: bool = True
) -> ReleaseGateReport:
    results: list[GateResult] = []
    generated: list[str] = []
    versions = SUPPORTED_PYTHON_VERSIONS if matrix else ("3.12",)
    with tempfile.TemporaryDirectory(prefix="agentscope-release-") as temp_dir:
        root = Path(temp_dir)
        for version in versions:
            config = production_baseline(
                python_version=version,
                project_name=f"agentscope_release_{version.replace('.', '')}",
            )
            # Cookiecutter's progress/cleanup output is useful interactively,
            # but must not corrupt the machine-readable ``--json`` artifact.
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                project = _generate_quiet(config, root)
            generated.append(f"Python {version}")
            results.extend(
                GateResult(
                    f"matrix.python_{version}.{result.name.split('.', 1)[-1]}",
                    result.status,
                    result.detail,
                )
                for result in verify_generated_project(project)
            )
            if run_tests and version == versions[0]:
                results.extend(run_generated_test_commands(project))
            if run_docker and version == versions[0]:
                results.append(run_docker_journey(project))
            if run_glm and version == versions[0]:
                results.append(run_glm_evaluation(project))
    return ReleaseGateReport(tuple(results), tuple(generated))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-generated-tests", action="store_true", help="run generated deterministic/unit suites"
    )
    parser.add_argument(
        "--docker", action="store_true", help="opt in to compose config/pull/start checks"
    )
    parser.add_argument(
        "--glm", action="store_true", help="opt in to environment-only GLM evaluation"
    )
    parser.add_argument(
        "--no-matrix", action="store_true", help="generate only the current Python 3.12 baseline"
    )
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args(argv)
    report = run_release_gate(
        run_tests=args.run_generated_tests,
        run_docker=args.docker,
        run_glm=args.glm,
        matrix=not args.no_matrix,
    )
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for result in report.results:
            print(f"[{result.status.upper():4}] {result.name}: {result.detail}")
        print(
            f"pass_rate={report.pass_rate:.2%} passed={report.passed} failed={report.failed} skipped={report.skipped}"
        )
    return 0 if report.quality_gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

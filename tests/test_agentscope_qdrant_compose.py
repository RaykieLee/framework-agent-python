"""Generated-compose checks for the curl-free Qdrant health probe."""

import re
from pathlib import Path

from fastapi_gen.generator import generate_project
from scripts.agentscope_release_gate import production_baseline


def test_generated_qdrant_healthchecks_support_the_slim_image(tmp_path: Path) -> None:
    """All generated Compose variants must use a probe present in Qdrant's image."""

    project = generate_project(production_baseline(project_name="qdrant_healthcheck"), tmp_path)

    for compose_name in ("docker-compose.yml", "docker-compose.dev.yml", "docker-compose.prod.yml"):
        compose = (project / compose_name).read_text(encoding="utf-8")
        qdrant_match = re.search(
            r"(?ms)^  qdrant:\n    image:.*?(?=^  [A-Za-z_][A-Za-z0-9_-]*:|\Z)", compose
        )
        assert qdrant_match is not None
        qdrant_block = qdrant_match.group(0)
        healthcheck = qdrant_block.split("    healthcheck:", 1)[1].split(
            "      interval:", 1
        )[0]
        healthcheck_command = healthcheck.split("      test:", 1)[1]
        assert "bash -c 'exec 3<>/dev/tcp/127.0.0.1/6333" in healthcheck_command
        assert 'case "$$line" in *200*)' in healthcheck_command
        assert "curl" not in healthcheck_command

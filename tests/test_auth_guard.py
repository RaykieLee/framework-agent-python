"""Regression tests for stale persisted auth state."""

from pathlib import Path

from fastapi_gen.generator import _find_template_dir


def _auth_guard_source() -> str:
    path = (
        _find_template_dir()
        / "{{cookiecutter.project_slug}}"
        / "frontend/src/components/layout/auth-guard.tsx"
    )
    return path.read_text(encoding="utf-8")


def _frontend_source(relative_path: str) -> str:
    path = _find_template_dir() / "{{cookiecutter.project_slug}}" / "frontend" / relative_path
    return path.read_text(encoding="utf-8")


def test_auth_guard_revalidates_persisted_sessions_on_mount() -> None:
    """Persisted Zustand state must not bypass the HTTP-only cookie check."""
    source = _auth_guard_source()

    assert "const [checking, setChecking] = useState(true);" in source
    assert "if (isAuthenticated) return;" not in source


def test_admin_login_redirects_to_management_panel() -> None:
    login = _frontend_source("src/hooks/use-auth.ts")
    assert "isAppAdmin(response.user) ? ROUTES.ADMIN : ROUTES.CHAT" in login

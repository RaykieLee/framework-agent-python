# Installation

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Install framework-agent-python

=== "uv (recommended)"

    ```bash
    uv tool install framework-agent-python
    ```

=== "pip"

    ```bash
    pip install framework-agent-python
    ```

=== "pipx"

    ```bash
    pipx install framework-agent-python
    ```

## Verify Installation

```bash
framework-agent-python --version
```

## Create Your First Project

Generate the project, then bring the whole backend up with a single command:

```bash
# 1. Generate your project — just answer the wizard's prompts
framework-agent-python

# 2. Backend + PostgreSQL up, migrations applied, default admin seeded
cd my_app
make bootstrap

# 3. Frontend (in a second terminal)
cd frontend && bun install && bun dev
```

That's it — backend at <http://localhost:8000>, API docs at `/docs`, frontend at <http://localhost:3000>, admin login `admin@example.com` / `admin123`.

`make bootstrap` (= `make dev` + `make seed`) builds the backend image, starts the Docker stack, waits for PostgreSQL, applies migrations, and seeds the admin user. It's idempotent — re-run it anytime.

### Other ways to generate

```bash
# Non-interactive with explicit options
framework-agent-python create my_app --database postgresql --frontend nextjs

# Presets (run `framework-agent-python templates` for the full list)
framework-agent-python create my_app --preset ai-agent

# Bare-bones project
framework-agent-python create my_app --minimal
```

## Available Presets

| Preset | Description |
|--------|-------------|
| `--preset production` | Full production setup with Redis, Sentry, Kubernetes, Prometheus |
| `--preset ai-agent` | AI agent with WebSocket streaming and conversation persistence |
| `--preset production-saas` | SaaS setup: billing, teams, and admin panel |
| `--minimal` | Minimal project with no extras |

## Next Steps

- [Quick Start](guides/quick-start.md) - Set up your development environment
- [Configuration](guides/configuration.md) - Learn about configuration options
- [AI Agents](ai-agent.md) - Configure AI frameworks

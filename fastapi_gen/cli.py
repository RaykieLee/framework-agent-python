"""?? AI Agent ?????? CLI ???"""

import subprocess
from pathlib import Path

import click
from click.core import ParameterSource
from rich.console import Console

from . import __version__
from .config import (
    AIFrameworkType,
    AuthMode,
    BackgroundTaskType,
    BillingModelType,
    CIType,
    DatabaseType,
    EmailProviderType,
    FrontendType,
    LLMProviderType,
    NewsletterProviderType,
    OAuthProvider,
    OrmType,
    PaymentProviderType,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    RerankerType,
    ReverseProxyType,
    TenancyMode,
    VectorStoreType,
)
from .generator import generate_project, post_generation_tasks
from .prompts import confirm_generation, run_interactive_prompts, show_summary

console = Console()


def _preflight_check(  # noqa: C901
    *,
    billing: bool,
    credits: bool,
    teams: bool,
    usage_dashboard: bool,
    anomaly_detection: bool,
    slack_alerts: bool,
    newsletter: bool,
    email: bool,
    rag: bool,
    database: str,
    vector_store: str,
    frontend: str,
    admin_panel: bool,
    marketing_site: bool,
    demo_export: bool,
    oauth_google: bool,
    gdrive_rag: bool,
    s3_rag: bool,
    task_queue: str,
    redis: bool,
    caching: bool,
    rate_limiting: bool,  # noqa: ARG001 — reserved for future pre-flight checks
    llm_provider: str,
) -> None:
    """Catch common flag conflicts BEFORE ProjectConfig validation.

    Pydantic raises one error at a time after parsing finishes. This pre-flight
    collects ALL conflicts and shows them with "Quick fix" hints, so users can
    correct everything in one go. Pydantic validators stay as the source of
    truth for programmatic use; this is purely UX polish.
    """
    issues: list[tuple[str, str]] = []  # (problem, quick_fix)

    # --- Teams / billing dependency chain ---
    if billing and not teams:
        issues.append(
            (
                "--billing ?? --teams?Stripe ????????",
                "?? --teams ??? --billing",
            )
        )
    if credits and not billing:
        issues.append(
            (
                "--credits ?? --billing???? Stripe ?????",
                "?? --billing --teams???? --credits?",
            )
        )
    if usage_dashboard and not credits:
        issues.append(
            (
                "--usage-dashboard ?? --credits??????????",
                "?? --credits --billing --teams",
            )
        )
    if anomaly_detection and not credits:
        issues.append(
            (
                "--anomaly-detection ?? --credits???????????",
                "?? --credits --billing --teams",
            )
        )
    if slack_alerts and not anomaly_detection:
        issues.append(
            (
                "--slack-alerts ?? --anomaly-detection????????????",
                "?? --anomaly-detection --credits --billing --teams",
            )
        )

    # --- Email / newsletter ---
    if newsletter and not email:
        issues.append(
            (
                "--newsletter ?? --email???????????????",
                "?? --email ??? --newsletter",
            )
        )

    # --- RAG dependency chain ---
    if rag and database == "none":
        issues.append(
            (
                "--rag ??????RAGDocument ?????????",
                "?? --database postgresql",
            )
        )
    if rag and vector_store == "pgvector" and database != "postgresql":
        issues.append(
            (
                f"--vector-store=pgvector requires --database=postgresql, got {database}",
                "??? --database postgresql ??? --vector-store milvus|qdrant|chromadb",
            )
        )
    if gdrive_rag and not rag:
        issues.append(
            (
                "--gdrive-rag ?? --rag?Drive ?????????????",
                "?? --rag",
            )
        )
    if s3_rag and not rag:
        issues.append(
            (
                "--s3-rag ?? --rag?S3 ?????????????",
                "?? --rag",
            )
        )

    # --- Frontend-dependent features ---
    if marketing_site and frontend == "none":
        issues.append(
            (
                "--marketing-site ?? --frontend nextjs????/??/?????? UI?",
                "?? --frontend nextjs ??? --marketing-site",
            )
        )
    if demo_export and frontend == "none":
        issues.append(
            (
                "--demo-export ?? --frontend nextjs??????? UI ??? HTML ??",
                "?? --frontend nextjs ??? --demo-export",
            )
        )
    if admin_panel and frontend == "none":
        click.echo(
            click.style(
                "⚠ --admin-panel: SQLAdmin UI lives in the frontend. "
                "Backend admin REST routes (/admin/users, /admin/conversations, etc.) "
                "still work without it — add --frontend nextjs for the visual panel.",
                fg="yellow",
            ),
            err=True,
        )
    if oauth_google and frontend == "none":
        issues.append(
            (
                "--oauth-google ?????????",
                "?? --frontend nextjs ??? --oauth-google",
            )
        )

    # --- Background queue / Redis ---
    if task_queue in ("celery", "taskiq", "arq") and not redis:
        issues.append(
            (
                f"--task-queue={task_queue} requires --redis (broker/result backend)",
                f"Add --redis (it'll auto-enable for queue={task_queue})",
            )
        )
    if caching and not redis:
        issues.append(
            (
                "--caching ?? --redis??????",
                "?? --redis ??? --caching",
            )
        )

    # --- Multi-LLM context ---
    if llm_provider == "all" and frontend == "none":
        # Not an error — just a warning. Skip for headless/API-only uses.
        click.echo(
            click.style(
                "⚠ --llm-provider=all is most useful with the chat UI provider switcher; "
                "?? --frontend ??'ll need to pick the model server-side per-request.",
                fg="yellow",
            ),
            err=True,
        )

    if not issues:
        return

    msg_lines = [
        click.style(
            f"✗ {len(issues)} conflicting flag combination{'s' if len(issues) > 1 else ''} found:",
            fg="red",
            bold=True,
        ),
        "",
    ]
    for i, (problem, fix) in enumerate(issues, 1):
        msg_lines.append(click.style(f"  {i}. {problem}", fg="red"))
        msg_lines.append(click.style(f"     ????? {fix}", fg="yellow"))
        msg_lines.append("")
    msg_lines.append(
        click.style(
            "?? `fastapi-fullstack templates` ??????????????",
            fg="cyan",
        )
    )
    raise click.UsageError("\n".join(msg_lines))


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="fastapi-fullstack")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """?? AI Agent ??????

    ??????? FastAPI + Next.js ????? AI Agent?
    WebSocket ?????20+ ???????????
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(new)


@cli.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="?????????",
)
@click.option(
    "--no-input",
    is_flag=True,
    default=False,
    help="??????????",
)
@click.option("--name", type=str, help="??????? --no-input ???")
@click.option(
    "--minimal",
    is_flag=True,
    default=False,
    help="Skip wizard — ask only for project name and use minimal defaults (PostgreSQL, no Docker/Redis/CI)",
)
def new(output: Path | None, no_input: bool, name: str | None, minimal: bool) -> None:
    """??????? FastAPI ???"""
    try:
        if no_input or minimal:
            if not name:
                if minimal:
                    import questionary

                    name = questionary.text(
                        "Project name:",
                        validate=lambda v: bool(v) or "名称不能为空",
                    ).ask()
                    if not name:
                        console.print("\n[yellow]????[/]")
                        return
                else:
                    console.print("[red]Error:[/] --name is required when using --no-input")
                    raise SystemExit(1)

            if minimal:
                config = ProjectConfig(
                    project_name=name,
                    database=DatabaseType.POSTGRESQL,
                    enable_logfire=False,
                    enable_redis=False,
                    enable_caching=False,
                    enable_rate_limiting=False,
                    enable_pagination=False,
                    enable_admin_panel=False,
                    enable_docker=False,
                    enable_kubernetes=False,
                    background_tasks=BackgroundTaskType.NONE,
                    ci_type=CIType.NONE,
                )
                console.print(f"[cyan]??????????[/] {name}")
                console.print("[dim]PostgreSQL · ? Docker · ? Redis · ? CI[/]")
                console.print()
            else:
                config = ProjectConfig(project_name=name, background_tasks=BackgroundTaskType.NONE)
        else:
            config = run_interactive_prompts()
            show_summary(config)

            if not confirm_generation():
                console.print("[yellow]????????[/]")
                return

        project_path = generate_project(config, output)
        post_generation_tasks(project_path, config)

    except KeyboardInterrupt:
        console.print("\n[yellow]????[/]")
        raise SystemExit(0) from None
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@cli.command()
@click.argument("name", type=str)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="????",
)
@click.option(
    "--database",
    type=click.Choice(["postgresql"]),
    default="postgresql",
    help="?????",
)
@click.option(
    "--orm",
    type=click.Choice(["sqlalchemy", "sqlmodel"]),
    default="sqlalchemy",
    help="ORM ??sqlalchemy ? sqlmodel?",
)
@click.option("--no-logfire", is_flag=True, help="?? Logfire ??")
@click.option("--no-docker", is_flag=True, help="?? Docker ??")
@click.option("--no-env", is_flag=True, help="?? .env ????")
@click.option("--minimal", is_flag=True, help="??????????????")
@click.option(
    "--frontend",
    type=click.Choice(["none", "nextjs"]),
    default="none",
    help="????",
)
@click.option(
    "--backend-port",
    type=int,
    default=8000,
    help="???????????8000?",
)
@click.option(
    "--frontend-port",
    type=int,
    default=3000,
    help="???????????3000?",
)
@click.option(
    "--timezone",
    type=str,
    default="UTC",
    help="IANA timezone (e.g. UTC, Europe/Warsaw, America/New_York)",
)
@click.option(
    "--db-pool-size",
    type=int,
    default=5,
    help="????????????5?",
)
@click.option(
    "--db-max-overflow",
    type=int,
    default=10,
    help="??????????????10?",
)
@click.option(
    "--ai-framework",
    type=click.Choice(
        ["none", "pydantic_ai", "langchain", "langgraph", "deepagents", "pydantic_deep"]
    ),
    default="pydantic_ai",
    help="AI ??????pydantic_ai???? none ??? SaaS?? AI/???",
)
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic", "google", "openrouter", "all"]),
    default="openai",
    help=(
        "LLM provider (default: openai). 'all' installs every SDK and lets users "
        "pick the model at runtime. openrouter requires pydantic_ai."
    ),
)
@click.option("--redis", is_flag=True, help="?? Redis")
@click.option("--caching", is_flag=True, help="??????? --redis?")
@click.option("--rate-limiting", is_flag=True, help="????")
@click.option("--admin-panel", is_flag=True, help="???????SQLAdmin?")
@click.option(
    "--admin-features",
    type=str,
    default=None,
    help=(
        "Comma-separated list of admin panel sections to enable "
        "(users,orgs,subs,usage,events,audit,health). "
        "Defaults to all sections when --admin-panel is set."
    ),
)
@click.option(
    "--task-queue",
    type=click.Choice(["none", "celery", "taskiq", "arq"]),
    default="none",
    help="??????",
)
@click.option("--oauth-google", is_flag=True, help="?? Google OAuth")
@click.option(
    "--auth-mode",
    type=click.Choice(["local", "delegated"]),
    default="local",
    help=(
        "local (default): backend handles email/password + optional OAuth. "
        "delegated: backend trusts JWTs from external IdP (Auth0/Clerk/Cognito/Keycloak) "
        "validated against a public JWKS URL. No registration UI, no password storage."
    ),
)
@click.option(
    "--shared-secret-jwt",
    is_flag=True,
    default=False,
    help=(
        "When --auth-mode=delegated: validate JWTs with a shared HMAC secret "
        "(HS256) instead of fetching public keys from a JWKS URL. Use when the "
        "client backend signs short-lived tokens for our API with a known secret."
    ),
)
@click.option(
    "--external-user-id",
    is_flag=True,
    default=False,
    help=(
        "When --auth-mode=delegated: denormalize the IdP `sub` onto Conversation "
        "rows so client APIs can list conversations by their user identifier "
        "without leaking internal UUIDs."
    ),
)
@click.option(
    "--websockets",
    is_flag=True,
    default=False,
    help="?? WebSocket ????? AI ?????",
)
@click.option(
    "--web-search",
    is_flag=True,
    default=False,
    help="?? AI Agent ? Web ?????Tavily?",
)
@click.option(
    "--web-fetch", is_flag=True, default=False, help="?? AI Agent ? Web ????"
)
@click.option(
    "--charts",
    is_flag=True,
    default=False,
    help="?? AI Agent ???????????/???/??/???/????",
)
@click.option(
    "--code-execution",
    is_flag=True,
    default=False,
    help="???? Monty ??? run_python ???????? PydanticAI?",
)
@click.option(
    "--skills",
    is_flag=True,
    default=False,
    help="???????SkillsToolset ? backend/skills/ ?? SKILL.md ???? PydanticAI?",
)
@click.option(
    "--deep-research",
    is_flag=True,
    default=False,
    help="?????? Agent?TODO ??? + ? Agent + ???????? PydanticAI?",
)
@click.option(
    "--mcp-client",
    is_flag=True,
    default=False,
    help="?? MCP ????????? MCP ????? Agent ???? PydanticAI?",
)
@click.option("--session-management", is_flag=True, help="??????")
@click.option(
    "--reverse-proxy",
    type=click.Choice(["none", "nginx", "traefik"]),
    default="nginx",
    help="??????????nginx???? nginx???????",
)
@click.option("--kubernetes", is_flag=True, help="?? Kubernetes ??")
@click.option(
    "--ci",
    type=click.Choice(["github", "gitlab", "none"]),
    default="github",
    help="CI/CD ??",
)
@click.option("--sentry", is_flag=True, help="?? Sentry ????")
@click.option("--prometheus", is_flag=True, help="?? Prometheus ??")
@click.option("--file-storage", is_flag=True, help="?? S3/MinIO ????")
@click.option("--webhooks", is_flag=True, help="?? Webhooks ??")
@click.option(
    "--langsmith",
    is_flag=True,
    help="?? LangSmith ?????LangChain/LangGraph/DeepAgents?",
)
@click.option(
    "--python-version",
    type=click.Choice(["3.11", "3.12", "3.13"]),
    default="3.12",
    help="Python ??",
)
@click.option(
    "--preset",
    type=click.Choice(
        [
            "production",
            "ai-agent",
            "production-saas",
            "b2b-multi-tenant",
            "internal-tool",
            "embedded-chatbot",
            "blog-saas",
            "consumer-app",
            "dev-playground",
        ]
    ),
    default=None,
    help=("????????? `fastapi-fullstack templates` ???????"),
)
@click.option(
    "--rag",
    is_flag=True,
    default=False,
    help="?? RAG ???",
)
@click.option(
    "--vector-store",
    type=click.Choice(["milvus", "qdrant", "chromadb", "pgvector"]),
    default="milvus",
    help="???????????milvus?",
)
@click.option(
    "--gdrive-rag",
    is_flag=True,
    default=False,
    help="?? Google Drive ??????",
)
@click.option(
    "--s3-rag",
    is_flag=True,
    default=False,
    help="?? S3/MinIO ??????",
)
@click.option(
    "--reranker",
    type=click.Choice(["none", "cohere", "cross_encoder"]),
    default="none",
    help="????????",
)
@click.option(
    "--pdf-parser",
    type=click.Choice(["pymupdf", "liteparse", "llamaparse", "all"]),
    default="pymupdf",
    help="PDF ????pymupdf=???liteparse=?? AI?llamaparse=???all=??????",
)
@click.option("--telegram", is_flag=True, default=False, help="?? Telegram ??")
@click.option("--slack", is_flag=True, default=False, help="?? Slack ??")
@click.option("--teams", is_flag=True, default=False, help="????/????")
@click.option(
    "--billing", is_flag=True, default=False, help="?? Stripe ????? --teams?"
)
@click.option(
    "--credits",
    is_flag=True,
    default=False,
    help="????????? --billing?",
)
@click.option(
    "--usage-dashboard",
    is_flag=True,
    default=False,
    help="?????????? --credits?",
)
@click.option(
    "--anomaly-detection",
    is_flag=True,
    default=False,
    help="??????????? --credits?",
)
@click.option(
    "--slack-alerts",
    is_flag=True,
    default=False,
    help="?? Slack ??????? --anomaly-detection?",
)
@click.option(
    "--billing-currency",
    type=str,
    default="usd",
    help="??????????usd?",
)
@click.option(
    "--trial-days",
    type=int,
    default=14,
    help="??????????14?",
)
@click.option(
    "--trial-requires-card/--no-trial-requires-card",
    default=True,
    help="??????????????????? --no-trial-requires-card ???????",
)
@click.option("--email", is_flag=True, default=False, help="??????")
@click.option(
    "--email-provider",
    type=click.Choice(["resend", "smtp", "log"]),
    default="log",
    help="?????????log?????????",
)
@click.option(
    "--newsletter",
    is_flag=True,
    default=False,
    help="??????????? --email?",
)
@click.option(
    "--marketing-site",
    is_flag=True,
    default=False,
    help="????/????",
)
@click.option(
    "--demo-export",
    is_flag=True,
    default=False,
    help="??? HTML ?????Vite ?? + ??????? --frontend?",
)
@click.option(
    "--i18n/--no-i18n",
    "i18n",
    default=True,
    help="Generate i18n infrastructure (next-intl + locale switcher). "
    "Disable for single-language English-only frontends.",
)
@click.option(
    "--example-resource",
    is_flag=True,
    default=False,
    help=(
        "Scaffold an example Item CRUD (model + repo + service + routes + "
        "migration) as a reference for adding new domains. "
        "Requires --database postgresql."
    ),
)
@click.option("--changelog", is_flag=True, default=False, help="????????")
@click.option("--testimonials", is_flag=True, default=False, help="????????")
@click.option(
    "--comparison-pages",
    is_flag=True,
    default=False,
    help="????????",
)
@click.option("--affiliate", is_flag=True, default=False, help="????????")
@click.option(
    "--status-badge", is_flag=True, default=False, help="???????/??????"
)
@click.option(
    "--allowed-email-domains",
    type=str,
    default="",
    help=(
        "Comma-separated email domains allowed to register via OAuth "
        "(e.g. 'example.com,acme.com'). Empty = allow all."
    ),
)
@click.option(
    "--seed-admin-email",
    type=str,
    default="",
    help="????????????????????? .env ?? FIRST_ADMIN_EMAIL??",
)
@click.option(
    "--embed-allowed-origins",
    type=str,
    default="",
    help=(
        "Comma-separated origins allowed to embed the app in an iframe "
        "(sets CSP frame-ancestors + CORS). Empty = 'frame-ancestors none'."
    ),
)
@click.option(
    "--brand-from-config",
    is_flag=True,
    default=False,
    help="???? BRAND_COLOR/BRAND_LOGO_URL ??????????/???????",
)
@click.option(
    "--newsletter-provider",
    type=click.Choice(["resend", "mailchimp", "convertkit"]),
    default="resend",
    help="?? --newsletter ?????????????resend??",
)
@click.option(
    "--tenancy",
    type=click.Choice(["single", "multi_org", "platform"]),
    default="single",
    help="??????single?????multi_org??? --teams??platform?",
)
@click.option(
    "--per-org-quotas",
    is_flag=True,
    default=False,
    help="???????????? --teams??",
)
@click.option(
    "--payment-provider",
    type=click.Choice(["stripe", "paddle", "lemonsqueezy", "polar"]),
    default="stripe",
    help="?????????stripe??? Stripe ??????",
)
@click.option(
    "--billing-model",
    type=click.Choice(["subscription", "usage", "hybrid", "one_time"]),
    default="subscription",
    help="????????subscription??hybrid = ???? + ????",
)
@click.option(
    "--storybook",
    is_flag=True,
    default=False,
    help="??????? Storybook ???",
)
def create(
    name: str,
    output: Path | None,
    database: str,
    orm: str,
    no_logfire: bool,
    no_docker: bool,
    no_env: bool,
    minimal: bool,
    frontend: str,
    backend_port: int,
    frontend_port: int,
    db_pool_size: int,
    db_max_overflow: int,
    ai_framework: str,
    llm_provider: str,
    # Optional features
    redis: bool,
    caching: bool,
    rate_limiting: bool,
    admin_panel: bool,
    admin_features: str | None,
    task_queue: str,
    oauth_google: bool,
    auth_mode: str,
    shared_secret_jwt: bool,
    external_user_id: bool,
    websockets: bool,
    web_search: bool,
    web_fetch: bool,
    charts: bool,
    code_execution: bool,
    skills: bool,
    deep_research: bool,
    mcp_client: bool,
    session_management: bool,
    reverse_proxy: str,
    kubernetes: bool,
    ci: str,
    sentry: bool,
    prometheus: bool,
    file_storage: bool,
    webhooks: bool,
    langsmith: bool,
    python_version: str,
    rag: bool,
    vector_store: str,
    gdrive_rag: bool,
    s3_rag: bool,
    reranker: str,
    pdf_parser: str,
    timezone: str,
    preset: str | None,
    telegram: bool,
    slack: bool,
    teams: bool,
    billing: bool,
    credits: bool,
    usage_dashboard: bool,
    anomaly_detection: bool,
    slack_alerts: bool,
    billing_currency: str,
    trial_days: int,
    trial_requires_card: bool,
    email: bool,
    email_provider: str,
    newsletter: bool,
    marketing_site: bool,
    demo_export: bool,
    i18n: bool,
    example_resource: bool,
    changelog: bool,
    testimonials: bool,
    comparison_pages: bool,
    affiliate: bool,
    status_badge: bool,
    allowed_email_domains: str,
    seed_admin_email: str,
    embed_allowed_origins: str,
    brand_from_config: bool,
    newsletter_provider: str,
    tenancy: str,
    per_org_quotas: bool,
    payment_provider: str,
    billing_model: str,
    storybook: bool,
) -> None:
    """?????????? FastAPI ???

    NAME is the project name (e.g., my_project)
    """
    try:
        # Handle presets first
        if preset == "production":
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_rate_limiting=True,
                enable_sentry=True,
                enable_prometheus=True,
                enable_docker=True,
                enable_kubernetes=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "ai-agent":
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_langsmith=ai_framework in ("langchain", "langgraph", "deepagents"),
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "production-saas":
            # Full SaaS stack: Stripe billing + credits + teams + admin + email +
            # Sentry + Kubernetes + GitHub Actions. Postgres + Redis + RAG-ready.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_rate_limiting=True,
                enable_sentry=True,
                enable_prometheus=True,
                enable_admin_panel=True,
                enable_session_management=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_langsmith=ai_framework in ("langchain", "langgraph", "deepagents"),
                enable_teams=True,
                enable_billing=True,
                enable_credits_system=True,
                enable_usage_dashboard=True,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_marketing_site=True,
                enable_docker=True,
                enable_kubernetes=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "b2b-multi-tenant":
            # B2B with workspaces, billing, credits, usage dashboard, admin.
            # Note: full scenario also wants invite-only signup + 2FA — those
            # require new --auth-mode flag which doesn't exist yet (see notes/
            # thingstofix.md §A). For now we ship session_management + admin so
            # account-takeover surface is reasonable.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_rate_limiting=True,
                enable_sentry=True,
                enable_admin_panel=True,
                enable_session_management=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=True,
                enable_billing=True,
                enable_credits_system=True,
                enable_usage_dashboard=True,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_marketing_site=False,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "internal-tool":
            # Internal tool / staff dashboard: SSO via Google OAuth, no public
            # signup landing pages, no billing. Teams + admin enabled. Note:
            # SSO-only enforcement (disable email/password registration) needs
            # --auth-mode=sso-only which is wishlist (see thingstofix §A).
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_admin_panel=True,
                enable_session_management=True,
                oauth_provider=OAuthProvider.GOOGLE,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=True,
                enable_billing=False,
                enable_marketing_site=False,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "embedded-chatbot":
            # Chat widget to be embedded in client's existing site. Delegated
            # auth — backend trusts JWTs from client's IdP (Auth0/Clerk/...).
            # No marketing pages, no teams, no billing. Note: --embed-mode
            # (widget loader + iframe-ready chat) is still wishlist; deployer
            # wires client-side embed integration manually.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                auth_mode=AuthMode.DELEGATED,
                enable_logfire=True,
                enable_redis=False,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=False,
                enable_billing=False,
                enable_marketing_site=False,
                enable_session_management=False,
                enable_admin_panel=False,
                background_tasks=BackgroundTaskType.NONE,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "blog-saas":
            # Content-first SaaS with auth + marketing/blog/legal. No AI/chat —
            # plain SaaS with newsletter, email, and public marketing pages.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=False,
                enable_redis=False,
                enable_websockets=False,
                ai_framework=AIFrameworkType.NONE,
                llm_provider=LLMProviderType.OPENAI,
                enable_teams=False,
                enable_billing=False,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_newsletter_signup=True,
                enable_marketing_site=True,
                enable_changelog=True,
                enable_admin_panel=False,
                background_tasks=BackgroundTaskType.NONE,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "consumer-app":
            # B2C consumer SaaS: OAuth login, marketing site, billing.
            # Note: --magic-link, --analytics=plausible|posthog, and
            # --billing=consumer (one-time purchases vs subscription) are
            # wishlist. For now we ship Google OAuth + Stripe subscription.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_sentry=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                oauth_provider=OAuthProvider.GOOGLE,
                enable_teams=True,
                enable_billing=True,
                enable_credits_system=True,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_marketing_site=True,
                enable_admin_panel=True,
                enable_session_management=True,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "dev-playground":
            # Local prototyping for AI features: PostgreSQL, no Docker, no CI,
            # ChromaDB (file-based vector store, no separate Milvus container).
            # Use this when iterating on agents/prompts/RAG locally without
            # spinning up the full production stack.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=False,
                enable_redis=False,
                enable_caching=False,
                enable_rate_limiting=False,
                enable_pagination=False,
                enable_admin_panel=False,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=False,
                enable_billing=False,
                enable_marketing_site=False,
                enable_docker=False,
                enable_kubernetes=False,
                background_tasks=BackgroundTaskType.NONE,
                ci_type=CIType.NONE,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif minimal:
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=False,
                enable_redis=False,
                enable_caching=False,
                enable_rate_limiting=False,
                enable_pagination=False,
                enable_admin_panel=False,
                enable_docker=False,
                enable_kubernetes=False,
                background_tasks=BackgroundTaskType.NONE,
                ci_type=CIType.NONE,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        else:
            # Pre-flight: catch common conflicting combinations BEFORE Pydantic
            # validation so users get all errors at once with quick-fix hints.
            # Pydantic still runs after this and is the source of truth.
            _preflight_check(
                billing=billing,
                credits=credits,
                teams=teams,
                usage_dashboard=usage_dashboard,
                anomaly_detection=anomaly_detection,
                slack_alerts=slack_alerts,
                newsletter=newsletter,
                email=email,
                rag=rag,
                database=database,
                vector_store=vector_store,
                frontend=frontend,
                admin_panel=admin_panel,
                marketing_site=marketing_site,
                demo_export=demo_export,
                oauth_google=oauth_google,
                gdrive_rag=gdrive_rag,
                s3_rag=s3_rag,
                task_queue=task_queue,
                redis=redis,
                caching=caching,
                rate_limiting=rate_limiting,
                llm_provider=llm_provider,
            )

            # Parse --admin-features comma-separated list
            _all_admin = {"users", "orgs", "subs", "usage", "events", "audit", "health"}
            if admin_features is not None:
                _chosen = {f.strip() for f in admin_features.split(",")} & _all_admin
            else:
                _chosen = _all_admin  # default: all enabled

            # Map --reverse-proxy shorthand to ReverseProxyType
            _rp_map = {
                "none": ReverseProxyType.NONE,
                "nginx": ReverseProxyType.NGINX_EXTERNAL,
                "traefik": ReverseProxyType.TRAEFIK_EXTERNAL,
            }

            # Full custom configuration with all options
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType(database),
                orm_type=OrmType(orm),
                enable_logfire=not no_logfire,
                enable_docker=not no_docker,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                db_pool_size=db_pool_size,
                db_max_overflow=db_max_overflow,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_redis=redis,
                enable_caching=caching,
                enable_rate_limiting=rate_limiting,
                enable_admin_panel=admin_panel,
                enable_admin_features_users="users" in _chosen,
                enable_admin_features_organizations="orgs" in _chosen,
                enable_admin_features_subscriptions="subs" in _chosen,
                enable_admin_features_usage="usage" in _chosen,
                enable_admin_features_stripe_events="events" in _chosen,
                enable_admin_features_audit_log="audit" in _chosen,
                enable_admin_features_system_health="health" in _chosen,
                background_tasks=BackgroundTaskType(task_queue),
                oauth_provider=OAuthProvider.GOOGLE if oauth_google else OAuthProvider.NONE,
                auth_mode=AuthMode(auth_mode),
                delegated_auth_use_shared_secret=shared_secret_jwt,
                enable_external_user_id_in_conversations=external_user_id,
                enable_websockets=websockets,
                enable_web_search=web_search,
                enable_web_fetch=web_fetch,
                enable_charts=charts,
                enable_code_execution=code_execution,
                enable_skills=skills,
                enable_deep_research=deep_research,
                enable_mcp_client=mcp_client,
                enable_session_management=session_management,
                reverse_proxy=_rp_map[reverse_proxy],
                enable_kubernetes=kubernetes,
                ci_type=CIType(ci),
                enable_sentry=sentry,
                enable_prometheus=prometheus,
                enable_file_storage=file_storage,
                enable_webhooks=webhooks,
                enable_langsmith=langsmith,
                python_version=python_version,
                timezone=timezone,
                rag_features=RAGFeatures(
                    enable_rag=rag,
                    vector_store=VectorStoreType(vector_store),
                    enable_google_drive_ingestion=gdrive_rag,
                    enable_s3_ingestion=s3_rag,
                    reranker_type=RerankerType(reranker),
                    pdf_parser=PdfParserType(pdf_parser),
                ),
                use_telegram=telegram,
                use_slack=slack,
                enable_teams=teams,
                enable_billing=billing,
                enable_credits_system=credits,
                enable_usage_dashboard=usage_dashboard,
                enable_usage_anomaly_detection=anomaly_detection,
                enable_slack_alerts=slack_alerts,
                billing_default_currency=billing_currency,
                billing_trial_days_default=trial_days,
                billing_trial_requires_card=trial_requires_card,
                enable_email=email,
                email_provider=EmailProviderType(email_provider),
                enable_newsletter_signup=newsletter,
                enable_marketing_site=marketing_site,
                enable_demo_export=demo_export,
                enable_i18n=i18n,
                include_example_crud=example_resource,
                enable_changelog=changelog,
                enable_testimonials=testimonials,
                enable_comparison_pages=comparison_pages,
                enable_affiliate_program=affiliate,
                enable_status_badge=status_badge,
                allowed_email_domains=allowed_email_domains,
                seed_admin_email=seed_admin_email,
                embed_allowed_origins=embed_allowed_origins,
                enable_brand_from_config=brand_from_config,
                newsletter_provider=NewsletterProviderType(newsletter_provider),
                tenancy=TenancyMode(tenancy),
                enable_per_org_quotas=per_org_quotas,
                payment_provider=PaymentProviderType(payment_provider),
                billing_model=BillingModelType(billing_model),
                enable_storybook=storybook,
            )

        console.print(f"[cyan]???????[/] {name}")
        if preset:
            console.print(f"[dim]??? {preset}[/]")
        console.print(f"[dim]???? {config.database.value}[/]")
        console.print("[dim]Auth: JWT + API Key[/]")
        if config.frontend != FrontendType.NONE:
            console.print(f"[dim]Frontend: {config.frontend.value}[/]")
        if config.ai_framework == AIFrameworkType.NONE:
            console.print("[dim]AI: disabled (plain SaaS)[/]")
        else:
            console.print(
                f"[dim]AI Agent: {config.ai_framework.value} ({config.llm_provider.value})[/]"
            )
        if config.background_tasks != BackgroundTaskType.NONE:
            console.print(f"[dim]Task Queue: {config.background_tasks.value}[/]")
        console.print()

        project_path = generate_project(config, output)
        post_generation_tasks(project_path, config)

    except ValueError as e:
        console.print(f"[red]?????[/] {e}")
        raise SystemExit(1) from None
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@cli.command()
def templates() -> None:
    """??????????"""
    console.print("[bold cyan]?? AI Agent ????????[/]")
    console.print()

    console.print("[bold]Presets:[/]")
    console.print("  --preset production       ?????????Redis?Sentry?K8s ??")
    console.print(
        "  --preset ai-agent         AI Agent + WebSocket ???? + ?????"
    )
    console.print(
        "  --preset production-saas  ?? SaaS?Stripe ?? + ?? + ?? + ?? + ?? + Sentry + K8s"
    )
    console.print(
        "  --preset b2b-multi-tenant  ???? + ?? + ?? + ????????????"
    )
    console.print(
        "  --preset internal-tool     ??????Google SSO + ?? + ??????/??"
    )
    console.print(
        "  --preset embedded-chatbot ??????????????'s site (no marketing/teams/billing)"
    )
    console.print(
        "  --preset blog-saas         ???? SaaS??? + ?? + ???? + ???????? AI?"
    )
    console.print("  --preset consumer-app      B2C ???OAuth + ?? + ?? + ??")
    console.print(
        "  --preset dev-playground    ?? AI ?????PostgreSQL + ? Docker/K8s?????"
    )
    console.print(
        "  --minimal                  ??????PostgreSQL?? Docker/K8s/CI?? Redis?"
    )
    console.print()

    console.print("[bold]????[/]")
    console.print("  --database postgresql  ?? asyncpg ? PostgreSQL???????")
    console.print("  --orm sqlalchemy       SQLAlchemy????")
    console.print("  --orm sqlmodel         SQLModel")
    console.print()

    console.print("[bold]Authentication (always included):[/]")
    console.print("  JWT + ???????/???????????")
    console.print("  API Key ???X-API-Key ???????????")
    console.print("  --oauth-google                 ?? Google OAuth")
    console.print("  --session-management           ??????")
    console.print(
        "  --auth-mode local              ?????????/?? + OAuth"
    )
    console.print(
        "  --auth-mode delegated          ???? IdP ??? JWT?Auth0/Clerk/Cognito/Keycloak?"
    )
    console.print(
        "  --shared-secret-jwt            ? delegated ?????? HMAC ?????? JWKS"
    )
    console.print(
        "  --external-user-id             ? delegated ????? Conversation ???? IdP sub"
    )
    console.print()

    console.print("[bold]AI Agent:[/]")
    console.print(
        "  --ai-framework none             ? AI??? SaaS??? agents/chat/conversations?"
    )
    console.print("  --ai-framework pydantic_ai      PydanticAI????")
    console.print("  --ai-framework langchain        LangChain")
    console.print("  --ai-framework langgraph        LangGraph?ReAct Agent?")
    console.print("  --ai-framework deepagents       DeepAgents??? Agent??????")
    console.print(
        "  --ai-framework pydantic_deep    PydanticDeep????? Agent?Docker ???"
    )
    console.print("  --llm-provider openai           OpenAI")
    console.print("  --llm-provider anthropic        Anthropic")
    console.print("  --llm-provider google           Google Gemini")
    console.print("  --llm-provider openrouter       OpenRouter?? pydantic_ai?")
    console.print(
        "  --websockets                    ?? WebSocket ????????????"
    )
    console.print("  --web-search                    ?? AI Agent ? Web ?????Tavily?")
    console.print("  --web-fetch                     ?? AI Agent ? Web ????")
    console.print()

    console.print("[bold]Background Tasks:[/]")
    console.print("  --task-queue none      ? FastAPI BackgroundTasks")
    console.print("  --task-queue celery    Celery????")
    console.print("  --task-queue taskiq    Taskiq??????")
    console.print("  --task-queue arq       ARQ?????")
    console.print()

    console.print("[bold]Frontend:[/]")
    console.print("  --frontend none        ? API?????")
    console.print("  --frontend nextjs      Next.js 15?App Router?TypeScript?Bun?????")
    console.print(
        "  --no-i18n              ????????????????"
    )
    console.print(
        "  --marketing-site       ????/???? (blog, pricing, legal)"
    )
    console.print("  --changelog            ????????")
    console.print()

    console.print("[bold]RAG (Retrieval Augmented Generation):[/]")
    console.print("  --rag                               ?? RAG")
    console.print("  --vector-store milvus|qdrant|chromadb|pgvector  ???????")
    console.print("  --gdrive-rag                        ?? Google Drive ????")
    console.print("  --s3-rag                            ?? S3/MinIO ????")
    console.print("  --reranker none|cohere|cross_encoder  ?????")
    console.print("  --pdf-parser pymupdf|liteparse|llamaparse  PDF ???")
    console.print()

    console.print("[bold]Integrations:[/]")
    console.print("  --redis            ?? Redis")
    console.print("  --caching          ??????? --redis?")
    console.print("  --rate-limiting    ????")
    console.print("  --admin-panel      ???????SQLAdmin?")
    console.print("  --admin-features users,orgs,subs,usage,events,audit,health")
    console.print("                     ???????????????????")
    console.print("  --file-storage     ?? S3/MinIO ????")
    console.print("  --webhooks         ?? Webhooks ??")
    console.print("  --telegram         ?? Telegram ?????")
    console.print("  --slack            ?? Slack ????")
    console.print()

    console.print("[bold]Authentication:[/]")
    console.print("  --allowed-email-domains example.com,acme.com")
    console.print("                     ?? OAuth ?????????")
    console.print("  --seed-admin-email admin@example.com")
    console.print("                     ??????????????????")
    console.print()

    console.print("[bold]Teams & Billing:[/]")
    console.print("  --teams            ???????")
    console.print("  --tenancy single|multi_org|platform  ?????????single?")
    console.print("  --billing          ??????? --teams?")
    console.print("  --payment-provider stripe|paddle|lemonsqueezy|polar????stripe?")
    console.print("  --billing-model subscription|usage|hybrid|one_time????subscription?")
    console.print("  --credits          ????????? --billing?")
    console.print("  --per-org-quotas   ???????????? --teams?")
    console.print("  --usage-dashboard  ?????????? --credits?")
    console.print("  --email            ??????")
    console.print("  --email-provider resend|smtp|log  ?????????log?")
    console.print("  --newsletter       ??????????? --email?")
    console.print("  --newsletter-provider resend|mailchimp|convertkit????resend?")
    console.print()

    console.print("[bold]Embedding & White-label:[/]")
    console.print("  --embed-allowed-origins https://app.example.com")
    console.print("                     ????????? iframe ???CSP + CORS?")
    console.print("  --brand-from-config")
    console.print(
        "                     ??????????????/??????"
    )
    console.print("  --storybook        ??????? Storybook ??")
    console.print()

    console.print("[bold]Observability:[/]")
    console.print("  --no-logfire       ?? Logfire ?? (PydanticAI)")
    console.print("  --langsmith        ?? LangSmith?LangChain/LangGraph/DeepAgents?")
    console.print("  --sentry           ?? Sentry ????")
    console.print("  --prometheus       ?? Prometheus ??")
    console.print()

    console.print("[bold]DevOps:[/]")
    console.print("  --no-docker                  ?? Docker ??")
    console.print("  --kubernetes                 ?? Kubernetes ??")
    console.print("  --reverse-proxy none         ????????????")
    console.print("  --reverse-proxy nginx        ?? Nginx ????????")
    console.print("  --reverse-proxy traefik      ??? Traefik ??")
    console.print("  --ci github                  GitHub Actions????")
    console.print("  --ci gitlab                  GitLab CI")
    console.print("  --ci none                    ? CI/CD")
    console.print()

    console.print("[bold]Scaffold:[/]")
    console.print("  --example-resource    ???? Item CRUD ???")
    console.print("                        ??? → ?? → ?? → ?? → ???")
    console.print("                        ?? --database postgresql")
    console.print()

    console.print("[bold]Other:[/]")
    console.print("  --python-version 3.11|3.12|3.13  Python ??")
    console.print("  --no-env           ?? .env ????")
    console.print("  --backend-port N   ????????8000?")
    console.print("  --frontend-port N  ????????3000?")


_PATH_OPTION = click.option(
    "--path",
    "project_path",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
    help="??????????????",
)


def _git_error_message(exc: subprocess.CalledProcessError) -> str:
    """Turn a failed git call into a message that keeps its stderr.

    Every git call in the upgrade runs with ``check=True`` and captured output, so a
    raw ``CalledProcessError`` would surface only the exit status and bury the actual
    reason (bad git version, unicode pathspec, …) in the swallowed stderr.
    """
    cmd = exc.cmd
    printable = " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else str(cmd)
    detail = exc.stderr
    if isinstance(detail, bytes):
        detail = detail.decode("utf-8", "replace")
    message = f"git command failed: {printable}"
    if detail and detail.strip():
        message += f"\n{detail.strip()}"
    return message


@cli.group(invoke_without_command=True)
@_PATH_OPTION
@click.option("--to", "to_version", default=None, help="????????????")
@click.option("--dry-run", is_flag=True, help="?????????????")
@click.option(
    "--with-new-features",
    is_flag=True,
    help="????????????????????",
)
@click.option(
    "--force",
    is_flag=True,
    help="???????????????????????????",
)
@click.pass_context
def upgrade(
    ctx: click.Context,
    project_path: Path,
    to_version: str | None,
    dry_run: bool,
    with_new_features: bool,
    force: bool,
) -> None:
    """?????????????????

    ?????????????????????``upgrade finalize`` ???????????
    """
    if ctx.invoked_subcommand is not None:
        # --path has a default, so "was it typed?" needs click's parameter source
        # rather than a None check — otherwise `upgrade --path X finalize` silently
        # finalizes the current directory instead of X.
        path_given = ctx.get_parameter_source("project_path") is not ParameterSource.DEFAULT
        misplaced = [
            name
            for name, given in (
                ("--path", path_given),
                ("--to", to_version is not None),
                ("--dry-run", dry_run),
                ("--with-new-features", with_new_features),
                ("--force", force),
            )
            if given
        ]
        if misplaced:
            # --path needs the opposite advice to the rest: the subcommands carry their
            # own --path, so it moves *after* the subcommand. Telling the user to put it
            # before (where they already had it, since that is what lands here) sends
            # them in a circle, and dropping it would finalize the wrong directory.
            fix = (
                f"Use `upgrade {ctx.invoked_subcommand} --path ...` — the subcommand has "
                "its own --path."
                if misplaced == ["--path"]
                else "Drop it, or run `upgrade` without a subcommand."
            )
            raise click.UsageError(
                f"{', '.join(misplaced)} applies to `upgrade`, not "
                f"`upgrade {ctx.invoked_subcommand}`. {fix}"
            )
        return

    from .upgrade.runner import UpgradeError, run_upgrade

    try:
        run_upgrade(
            project_path,
            to_version=to_version,
            dry_run=dry_run,
            with_new_features=with_new_features,
            force=force,
        )
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(_git_error_message(exc)) from exc
    except (UpgradeError, FileNotFoundError, RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@upgrade.command("finalize")
@_PATH_OPTION
def upgrade_finalize(project_path: Path) -> None:
    """??????????????"""
    from .upgrade.runner import UpgradeError, run_finalize

    try:
        run_finalize(project_path)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(_git_error_message(exc)) from exc
    except (UpgradeError, FileNotFoundError, RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@upgrade.command("recover")
@_PATH_OPTION
def upgrade_recover(project_path: Path) -> None:
    """????????????????????"""
    from .upgrade.runner import run_recover

    try:
        run_recover(project_path)
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        raise click.ClickException(_git_error_message(exc)) from exc
    except (FileNotFoundError, RuntimeError) as exc:  # pragma: no cover
        raise click.ClickException(str(exc)) from exc


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()

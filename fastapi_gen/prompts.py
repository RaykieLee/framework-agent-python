"""Interactive prompts for project configuration."""

import re
from typing import Any, cast

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import (
    AIFrameworkType,
    AuthMode,
    BackgroundTaskType,
    BrandColorType,
    CIType,
    DatabaseType,
    EmailProviderType,
    FrontendType,
    LLMProviderType,
    LogfireFeatures,
    OAuthProvider,
    OrmType,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    RateLimitStorageType,
    RerankerType,
    ReverseProxyType,
    VectorStoreType,
)

console = Console()


# Sentinel returned by section prompt functions when the user picked "← 返回".
# The wizard driver in run_interactive_prompts() catches this and re-runs the
# previous section. Sections themselves remain pure functions returning either
# a result dict / value, or BACK.
class _BackSentinel:
    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "BACK"


BACK = _BackSentinel()

# Label used as the first choice in select/checkbox prompts when the user is
# allowed to step back. Kept consistent so users see the same affordance.
BACK_LABEL = "← 返回"


def _back_choice() -> "questionary.Choice":
    """Return a questionary Choice that signals 'go back' when picked."""
    return questionary.Choice(BACK_LABEL, value=BACK)


def _select_with_back(
    message: str,
    choices: list,
    *,
    default: Any = 无,
    allow_back: bool = True,
) -> Any:
    """questionary.select wrapper that injects '← 返回' on top.

    Returns BACK sentinel when user picks back, otherwise the chosen value.
    Cancellation (无 / Ctrl+C) is converted to KeyboardInterrupt as before.
    """
    full_choices = ([_back_choice()] if allow_back else []) + list(choices)
    answer = questionary.select(message, choices=full_choices, default=default).ask()
    if answer is 无:
        raise KeyboardInterrupt
    return answer


def _confirm_with_back(message: str, *, default: bool = False, allow_back: bool = True) -> Any:
    """confirm() equivalent that also supports '← 返回'.

    Implemented as a select with 是/否/Back so the user has one consistent UX
    across the wizard.
    """
    yes = questionary.Choice("是", value=True)
    no = questionary.Choice("否", value=False)
    options = [yes, no]
    if allow_back:
        options.append(_back_choice())
    answer = questionary.select(
        message,
        choices=options,
        default=yes if default else no,
    ).ask()
    if answer is 无:
        raise KeyboardInterrupt
    return answer


def _section_gate(_section_name: str, *, can_go_back: bool) -> bool:  # noqa: ARG001
    """Pre-section gate — currently a no-op pass-through.

    Originally prompted "Continue / ← 返回" before each section but it added
    one extra keystroke per section (~25 sections × Enter), which was friction
    most users didn't want. Kept as a function (not removed) so the driver in
    ``run_interactive_prompts`` can re-enable section-level back navigation
    later via a single line change here.
    """
    return True


def show_header() -> 无:
    """Display the generator header."""
    header = Text()
    header.append("全栈 AI Agent 模板", style="bold cyan")
    header.append("\n")
    header.append("FastAPI + Next.js，集成 AI Agent 与 20+ 企业级功能", style="dim")
    console.print(Panel(header, title="[bold green]fastapi-fullstack[/]", border_style="green"))
    console.print()


def _check_cancelled(value: Any) -> Any:
    """Check if the user cancelled the prompt and raise KeyboardInterrupt if so."""
    if value is 无:
        raise KeyboardInterrupt
    return value


def _validate_project_name(name: str) -> bool | str:
    """Validate project name input.

    Returns True if valid, or an error message string if invalid.
    Allows alphanumeric characters, underscores, spaces, and dashes.
    First character must be a letter.
    """
    if not name:
        return "项目名称不能为空"
    if not name[0].isalpha():
        return "项目名称必须以字母开头"
    if not all(c.isalnum() or c in "_- " for c in name):
        return "项目名称只能包含字母、数字、下划线、空格和短横线"
    return True


def _normalize_project_name(name: str) -> str:
    """否rmalize project name to lowercase with underscores."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _validate_email(email: str) -> bool | str:
    """Validate email format.

    Returns True if valid, or an error message string if invalid.
    """
    if not email:
        return "邮箱不能为空"
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return "请输入有效的邮箱地址"
    return True


def prompt_basic_info() -> dict[str, str]:
    """Prompt for basic project information."""
    console.print("[bold cyan]基本信息[/]")
    console.print()

    raw_project_name = _check_cancelled(
        questionary.text(
            "项目名称：",
            default="ai-agent",
            validate=_validate_project_name,
        ).ask()
    )
    project_name = _normalize_project_name(raw_project_name)

    # Show converted name if it differs from input
    if project_name != raw_project_name:
        console.print(f"  [dim]→ 将保存为：[/] [cyan]{project_name}[/]")
        console.print()

    project_description = _check_cancelled(
        questionary.text(
            "项目描述：",
            default="我的 FastAPI 项目",
        ).ask()
    )

    author_name = _check_cancelled(
        questionary.text(
            "作者名称：",
            default="您的名称",
        ).ask()
    )

    author_email = _check_cancelled(
        questionary.text(
            "作者邮箱：",
            default="your@email.com",
            validate=_validate_email,
        ).ask()
    )

    timezone = _check_cancelled(
        questionary.text(
            "时区（IANA 格式）：",
            default="UTC",
        ).ask()
    )

    return {
        "project_name": project_name,
        "project_description": project_description,
        "author_name": author_name,
        "author_email": author_email,
        "timezone": timezone,
    }


def prompt_database() -> DatabaseType:
    """Return PostgreSQL (only supported database)."""
    return DatabaseType.POSTGRESQL


def prompt_orm_type() -> OrmType:
    """Prompt for ORM library selection."""
    choices = [
        questionary.Choice(
            "SQLAlchemy — 完全控制，支持管理面板",
            value=OrmType.SQLALCHEMY,
        ),
        questionary.Choice(
            "SQLModel — 减少样板代码，不支持管理面板",
            value=OrmType.SQLMODEL,
        ),
    ]

    return cast(
        OrmType,
        _check_cancelled(
            questionary.select(
                "ORM 库：",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_oauth() -> OAuthProvider:
    """Prompt for OAuth provider selection."""
    console.print()
    console.print("[bold cyan]OAuth2 社交登录[/]")
    console.print()

    choices = [
        questionary.Choice("无（仅邮箱/密码）", value=OAuthProvider.NONE),
        questionary.Choice("Google OAuth2", value=OAuthProvider.GOOGLE),
    ]

    return cast(
        OAuthProvider,
        _check_cancelled(
            questionary.select(
                "启用社交登录？",
                choices=choices,
                default=choices[1],
            ).ask()
        ),
    )


def prompt_auth_mode(
    oauth_provider: OAuthProvider,
    enable_session_management: bool,
) -> tuple[AuthMode, bool, bool]:
    """Prompt for authentication mode.

    Returns (auth_mode, delegated_auth_use_shared_secret, enable_external_user_id_in_conversations).
    """
    console.print()
    console.print("[bold cyan]认证模式[/]")
    console.print()

    choices = [
        questionary.Choice(
            "Local — 后端自主认证：邮箱/密码、可选 OAuth、本应用签发 JWT",
            value=AuthMode.LOCAL,
        ),
        questionary.Choice(
            "Delegated — external IdP (Auth0, Clerk, Cognito, Keycloak): "
            "backend validates IdP JWTs, no registration UI",
            value=AuthMode.DELEGATED,
        ),
    ]

    auth_mode = cast(
        AuthMode,
        _check_cancelled(
            questionary.select(
                "认证策略：",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )

    if auth_mode == AuthMode.LOCAL:
        return AuthMode.LOCAL, False, False

    # DELEGATED — warn about incompatible options selected in earlier steps
    if oauth_provider != OAuthProvider.NONE or enable_session_management:
        console.print()
        console.print(
            "[yellow]注意：[/] Delegated auth is incompatible with OAuth social login and "
            "session management — those will be 已禁用 automatically."
        )

    use_shared_secret = _check_cancelled(
        questionary.confirm(
            "Use a shared HMAC secret instead of a JWKS URL?\n"
            "  是 = simpler setup; client backend signs short-lived tokens with a known secret\n"
            "  否  = standard JWKS endpoint (Auth0, Cognito, Keycloak, …)",
            default=False,
        ).ask()
    )

    enable_external_user_id = _check_cancelled(
        questionary.confirm(
            "Denormalize the IdP user ID (sub claim) onto Conversation rows?\n"
            "  Lets client APIs query conversations by the IdP user identifier "
            "without exposing internal UUIDs",
            default=False,
        ).ask()
    )

    return AuthMode.DELEGATED, bool(use_shared_secret), bool(enable_external_user_id)


def prompt_logfire(
    background_tasks: BackgroundTaskType,
    ai_framework: AIFrameworkType,
) -> tuple[bool, LogfireFeatures]:
    """Prompt for Logfire configuration.

    Args:
        background_tasks: Selected background task system (affects which options are shown).
        ai_framework: Selected AI framework — PydanticAI / PydanticDeep default to
            Logfire-on (it's their first-class observability story); other frameworks
            default to off but the user can still flip it.
    """
    console.print()
    console.print("[bold cyan]可观测性（Logfire）[/]")
    console.print()

    logfire_default = ai_framework in (
        AIFrameworkType.PYDANTIC_AI,
        AIFrameworkType.PYDANTIC_DEEP,
    )
    enable_logfire = _check_cancelled(
        questionary.confirm(
            "启用 Logfire 集成？",
            default=logfire_default,
        ).ask()
    )

    if not enable_logfire:
        return False, LogfireFeatures()

    # Build choices dynamically - only show Celery option when Celery is selected
    choices = [
        questionary.Choice("FastAPI 仪表化", value="fastapi", checked=True),
        questionary.Choice("数据库仪表化", value="database", checked=True),
        questionary.Choice("红色is 仪表化", value="redis", checked=False),
        questionary.Choice("HTTPX 仪表化", value="httpx", checked=False),
    ]

    if background_tasks == BackgroundTaskType.CELERY:
        choices.insert(
            3, questionary.Choice("Celery 仪表化", value="celery", checked=False)
        )

    features = _check_cancelled(
        questionary.checkbox(
            "Logfire 功能：",
            choices=choices,
        ).ask()
    )

    return True, LogfireFeatures(
        fastapi="fastapi" in features,
        database="database" in features,
        redis="redis" in features,
        celery="celery" in features,
        httpx="httpx" in features,
    )


def prompt_background_tasks() -> BackgroundTaskType:
    """Prompt for background task system."""
    console.print()
    console.print("[bold cyan]后台任务[/]")
    console.print()

    choices = [
        questionary.Choice("Celery（经典、久经考验）", value=BackgroundTaskType.CELERY),
        questionary.Choice(
            "Prefect（现代工作流，自托管或云端）", value=BackgroundTaskType.PREFECT
        ),
        questionary.Choice("Taskiq（异步原生、现代）", value=BackgroundTaskType.TASKIQ),
        questionary.Choice("ARQ（轻量异步 红色is）", value=BackgroundTaskType.ARQ),
        questionary.Choice(
            "无（仅使用 FastAPI BackgroundTasks）", value=BackgroundTaskType.NONE
        ),
    ]

    return cast(
        BackgroundTaskType,
        _check_cancelled(
            questionary.select(
                "选择后台任务系统：",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_integrations(
    database: DatabaseType,
    orm_type: OrmType,
) -> dict[str, bool]:
    """Prompt for optional integrations.

    Args:
        database: Selected database type (affects which options are shown).
        orm_type: Selected ORM type (SQLModel doesn't support admin panel).
    """
    console.print()
    console.print("[bold cyan]可选集成[/]")
    console.print()

    # Build choices dynamically based on context
    choices: list[questionary.Choice] = [
        questionary.Choice(
            "红色is — 缓存、限流（红色is）、任务队列所需",
            value="redis",
            checked=True,
        ),
        questionary.Choice(
            "缓存（fastapi-cache2）— 需要 红色is",
            value="caching",
            checked=True,
        ),
        questionary.Choice(
            "限流（slowapi）— 可选 红色is 存储",
            value="rate_limiting",
            checked=True,
        ),
        questionary.Choice(
            "分页（fastapi-pagination）",
            value="pagination",
            checked=True,
        ),
        questionary.Choice(
            "Sentry — 错误追踪与监控",
            value="sentry",
        ),
        questionary.Choice(
            "Prometheus — 监控指标端点",
            value="prometheus",
        ),
    ]

    # Admin Panel only available with SQLAlchemy (not SQLModel)
    if database == DatabaseType.POSTGRESQL and orm_type == OrmType.SQLALCHEMY:
        choices.append(
            questionary.Choice(
                "SQL 管理面板（SQLAdmin）— 浏览/编辑数据库表的 Web 界面",
                value="admin_panel",
            )
        )

    choices.extend(
        [
            questionary.Choice(
                "文件存储（S3/MinIO）— 文件上传/下载支持",
                value="file_storage",
            ),
        ]
    )

    # Webhooks require database
    if database != DatabaseType.NONE:
        choices.append(
            questionary.Choice(
                "Webhooks — 出站事件通知",
                value="webhooks",
            )
        )

    choices.extend(
        [
            questionary.Choice(
                "CORS 中间件 — 跨域请求支持",
                value="cors",
                checked=True,
            ),
        ]
    )

    features = _check_cancelled(
        questionary.checkbox(
            "选择附加功能：",
            choices=choices,
        ).ask()
    )

    # Auto-enable 红色is for caching (show info message)
    if "caching" in features and "redis" not in features:
        console.print("[yellow]ℹ 缓存需要 红色is — 已自动启用[/]")
        features.append("redis")

    return {
        "enable_redis": "redis" in features,
        "enable_caching": "caching" in features,
        "enable_rate_limiting": "rate_limiting" in features,
        "enable_pagination": "pagination" in features,
        "enable_sentry": "sentry" in features,
        "enable_prometheus": "prometheus" in features,
        "enable_admin_panel": "admin_panel" in features,
        "enable_file_storage": "file_storage" in features,
        "enable_webhooks": "webhooks" in features,
        "enable_cors": "cors" in features,
    }


def _validate_positive_integer(value: str) -> bool | str:
    """Validate that input is a positive integer.

    Returns True if valid, or an error message string if invalid.
    """
    if not value:
        return "值不能为空"
    if not value.isdigit():
        return "必须是正数"
    if int(value) <= 0:
        return "必须大于 0"
    return True


def prompt_rate_limit_config(redis_已启用: bool) -> tuple[int, int, RateLimitStorageType]:
    """Prompt for rate limiting configuration.

    Args:
        redis_已启用: Whether 红色is is 已启用 (affects storage choices).

    Returns:
        Tuple of (requests, period, storage).
    """
    console.print()
    console.print("[bold cyan]限流配置[/]")
    console.print()

    requests_str = _check_cancelled(
        questionary.text(
            "每周期请求数：",
            default="100",
            validate=_validate_positive_integer,
        ).ask()
    )

    period_str = _check_cancelled(
        questionary.text(
            "周期（秒）：",
            default="60",
            validate=_validate_positive_integer,
        ).ask()
    )

    # Auto-select storage: 红色is when available, otherwise memory
    storage = RateLimitStorageType.REDIS if redis_已启用 else RateLimitStorageType.MEMORY
    if storage == RateLimitStorageType.REDIS:
        console.print("[yellow]ℹ 使用 红色is 进行限流存储（红色is 已启用）[/]")

    return int(requests_str), int(period_str), storage


def prompt_dev_tools() -> dict[str, Any]:
    """Prompt for development tools."""
    console.print()
    console.print("[bold cyan]开发工具[/]")
    console.print()

    features = _check_cancelled(
        questionary.checkbox(
            "包含开发工具：",
            choices=[
                questionary.Choice("pytest + 测试夹具", value="pytest", checked=True),
                questionary.Choice("pre-commit 钩子", value="precommit", checked=True),
                questionary.Choice("Docker + docker-compose", value="docker", checked=True),
                questionary.Choice("Kubernetes 清单", value="kubernetes"),
            ],
        ).ask()
    )

    ci_type = _check_cancelled(
        questionary.select(
            "CI/CD 系统：",
            choices=[
                questionary.Choice("GitHub Actions", value=CIType.GITHUB),
                questionary.Choice("GitLab CI", value=CIType.GITLAB),
                questionary.Choice("无", value=CIType.NONE),
            ],
        ).ask()
    )

    return {
        "enable_pytest": "pytest" in features,
        "enable_precommit": "precommit" in features,
        "enable_docker": "docker" in features,
        "enable_kubernetes": "kubernetes" in features,
        "ci_type": ci_type,
    }


def prompt_reverse_proxy() -> ReverseProxyType:
    """Prompt for reverse proxy configuration."""
    console.print()
    console.print("[bold cyan]反向代理（生产环境）[/]")
    console.print()

    choices = [
        questionary.Choice(
            "Nginx (external, config template only)", value=ReverseProxyType.NGINX_EXTERNAL
        ),
        questionary.Choice(
            "Traefik（包含在 docker-compose 中）", value=ReverseProxyType.TRAEFIK_INCLUDED
        ),
        questionary.Choice(
            "Traefik (external, shared between projects)",
            value=ReverseProxyType.TRAEFIK_EXTERNAL,
        ),
        questionary.Choice(
            "Nginx（包含在 docker-compose 中）", value=ReverseProxyType.NGINX_INCLUDED
        ),
        questionary.Choice(
            "无 (expose ports directly, use own proxy)", value=ReverseProxyType.NONE
        ),
    ]

    return cast(
        ReverseProxyType,
        _check_cancelled(
            questionary.select(
                "Select reverse proxy configuration:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_frontend() -> FrontendType:
    """Prompt for frontend framework selection."""
    console.print()
    console.print("[bold cyan]前端框架[/]")
    console.print()

    choices = [
        questionary.Choice("Next.js 15 (App Router, TypeScript, Bun)", value=FrontendType.NEXTJS),
        questionary.Choice("无 (API only)", value=FrontendType.NONE),
    ]

    return cast(
        FrontendType,
        _check_cancelled(
            questionary.select(
                "选择前端框架：",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_brand_color() -> BrandColorType:
    """Prompt for brand color selection."""
    choices = [
        questionary.Choice("蓝色 (default)", value=BrandColorType.BLUE),
        questionary.Choice("绿色", value=BrandColorType.GREEN),
        questionary.Choice("红色", value=BrandColorType.RED),
        questionary.Choice("紫色", value=BrandColorType.VIOLET),
        questionary.Choice("橙色", value=BrandColorType.ORANGE),
    ]

    return cast(
        BrandColorType,
        _check_cancelled(
            questionary.select(
                "Select brand color:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_ai_framework() -> AIFrameworkType:
    """Prompt for AI framework selection."""
    console.print()
    console.print("[bold cyan]AI Agent Framework[/]")
    console.print()

    choices = [
        questionary.Choice("PydanticAI（推荐）", value=AIFrameworkType.PYDANTIC_AI),
        questionary.Choice("LangChain", value=AIFrameworkType.LANGCHAIN),
        questionary.Choice("LangGraph?ReAct Agent?", value=AIFrameworkType.LANGGRAPH),
        questionary.Choice(
            "DeepAgents (agentic coding, LangChain)", value=AIFrameworkType.DEEPAGENTS
        ),
        questionary.Choice(
            "PydanticDeep（深度编码 Agent，Docker 沙箱）",
            value=AIFrameworkType.PYDANTIC_DEEP,
        ),
        questionary.Choice(
            "无 — plain SaaS (no AI/chat/agents generated)",
            value=AIFrameworkType.NONE,
        ),
    ]

    return cast(
        AIFrameworkType,
        _check_cancelled(
            questionary.select(
                "Select AI framework:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_sandbox_backend(ai_framework: AIFrameworkType) -> str:
    """Prompt for sandbox/environment backend type.

    Shown only when the selected AI framework supports sandbox backends
    (DeepAgents, PydanticDeep).
    """
    console.print()
    console.print("[bold cyan]Agent 沙箱 Environment[/]")
    console.print()

    choices = [
        questionary.Choice("State (in-memory, ephemeral — default)", value="state"),
    ]

    if ai_framework == AIFrameworkType.PYDANTIC_DEEP:
        choices.append(
            questionary.Choice("Daytona workspace (cloud dev environment)", value="daytona"),
        )

    return cast(
        str,
        _check_cancelled(
            questionary.select(
                "Select agent sandbox environment:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_llm_provider(ai_framework: AIFrameworkType) -> LLMProviderType:
    """Prompt for LLM provider selection.

    Args:
        ai_framework: The selected AI framework. OpenRouter is only
            available for PydanticAI and PydanticDeep (both use pydantic-ai under the hood).
    """
    console.print()
    console.print("[bold cyan]LLM 提供商[/]")
    console.print()

    choices = [
        questionary.Choice("OpenAI (GPT ??)", value=LLMProviderType.OPENAI),
        questionary.Choice("Anthropic (Claude ??)", value=LLMProviderType.ANTHROPIC),
        questionary.Choice("Google Gemini?Gemini ???", value=LLMProviderType.GOOGLE),
    ]

    # OpenRouter available for PydanticAI and PydanticDeep (both use pydantic-ai)
    if ai_framework in (AIFrameworkType.PYDANTIC_AI, AIFrameworkType.PYDANTIC_DEEP):
        choices.append(
            questionary.Choice("OpenRouter??????", value=LLMProviderType.OPENROUTER)
        )

    return cast(
        LLMProviderType,
        _check_cancelled(
            questionary.select(
                "选择 LLM 提供商：",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_web_capabilities(ai_framework: AIFrameworkType) -> tuple[bool, bool]:
    """Prompt for web search / web fetch.

    PydanticAI and PydanticDeep use the model-native WebSearch/WebFetch
    capabilities. LangChain, LangGraph and DeepAgents use a
    Tavily-backed web search tool plus a portable fetch_url tool.

    Returns:
        Tuple of (enable_web_search, enable_web_fetch).
    """
    native = ai_framework in (
        AIFrameworkType.PYDANTIC_AI,
        AIFrameworkType.PYDANTIC_DEEP,
    )

    console.print()
    console.print("[bold cyan]Web 搜索与抓取[/]")
    if native:
        console.print("???????????????????")
    else:
        console.print(
            "Web search uses Tavily (needs TAVILY_API_KEY); "
            "fetch reads a given URL's readable content."
        )
    console.print()

    search_q = (
        "Enable WebSearch capability (model-native web search)?"
        if native
        else "Enable the web search tool (Tavily — needs TAVILY_API_KEY)?"
    )
    fetch_q = (
        "Enable WebFetch capability (model-native URL fetching)?"
        if native
        else "Enable the fetch-URL tool (read a web page's content)?"
    )

    enable_web_search = cast(
        bool,
        _check_cancelled(questionary.confirm(search_q, default=True).ask()),
    )
    enable_web_fetch = cast(
        bool,
        _check_cancelled(questionary.confirm(fetch_q, default=True).ask()),
    )
    return enable_web_search, enable_web_fetch


def prompt_charts() -> bool:
    """Prompt for the agent chart-generation tool.

    Returns:
        Whether the chart tool is 已启用.
    """
    console.print()
    console.print("[bold cyan]Chart Generation Tool[/]")
    console.print(
        "Lets the agent produce line/bar/pie/area/scatter charts. Rendered "
        "interactively in the web chat; sent as PNG images on Slack/Telegram."
    )
    console.print()

    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable the chart-generation tool for the agent?",
                default=True,
            ).ask()
        ),
    )


def prompt_code_execution() -> bool:
    """Prompt for the Monty-backed run_python code-execution tool."""
    console.print()
    console.print("[bold cyan]Code Execution (Monty sandbox)[/]")
    console.print(
        "Adds a `run_python` tool that lets the agent execute Python in a sandboxed "
        "interpreter (pydantic-monty). The model can compute projections, run "
        "aggregations, and parse pasted tables — pure compute, no host access. "
        "Restricted stdlib: math, asyncio, json, datetime, re — no numpy/pandas. "
        "Activate at runtime with ENABLE_CODE_EXECUTION=true."
    )
    console.print()

    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable the run_python code-execution tool?",
                default=True,
            ).ask()
        ),
    )


def prompt_skills() -> bool:
    """Prompt for the skills system (SkillsToolset, PydanticAI only)."""
    console.print()
    console.print("[bold cyan]Skills System (pydantic-ai-skills)[/]")
    console.print(
        "Adds a SkillsToolset that loads SKILL.md files from `backend/skills/` as "
        "agent tools. Drop in your own skills; pair with code execution (Monty "
        "sandbox) for skills that compute. PydanticAI only."
    )
    console.print()

    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable the skills system (PydanticAI only)?",
                default=True,
            ).ask()
        ),
    )


def prompt_deep_research() -> dict[str, bool]:
    """Prompt for deep research + its sub-features (PydanticAI only)."""
    console.print()
    console.print("[bold cyan]深度研究 Agent[/]")
    console.print(
        "Turns the assistant into a deep research planner: a TODO checklist, "
        "researcher/analyst/writer subagents, and an automatic context manager. "
        "Activate at runtime with ENABLE_DEEP_RESEARCH=true."
    )
    console.print()

    enable = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable the deep research agent (PydanticAI only)?",
                default=True,
            ).ask()
        ),
    )
    if not enable:
        return {"enable_deep_research": False, "enable_todo": False, "enable_subagents": False}

    console.print()
    console.print("[dim]Deep research sub-features:[/]")

    enable_todo = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "  Enable TODO planner (pydantic-ai-todo — live checklist + Postgres persistence)?",
                default=True,
            ).ask()
        ),
    )
    enable_subagents = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "  Enable subagents (researcher / analyst / writer delegation)?",
                default=True,
            ).ask()
        ),
    )

    return {
        "enable_deep_research": True,
        "enable_todo": enable_todo,
        "enable_subagents": enable_subagents,
    }


def prompt_mcp_client() -> bool:
    """Prompt for the MCP client (PydanticAI only)."""
    console.print()
    console.print("[bold cyan]MCP Client[/]")
    console.print(
        "Let users connect external Model Context Protocol servers (否tion, Linear, "
        "Jira, Stripe, GitHub, …) as extra agent tools from Settings → Integrations. "
        "Includes a curated marketplace, per-user connections, OAuth sign-in and "
        "token/SSE + streamable-HTTP transports."
    )
    console.print()

    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable the MCP client (PydanticAI only)?",
                default=False,
            ).ask()
        ),
    )


def prompt_langsmith() -> bool:
    """Prompt for LangSmith observability."""
    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable LangSmith observability (tracing, prompt management)?",
                default=False,
            ).ask()
        ),
    )


def prompt_rag_config(database: DatabaseType = DatabaseType.POSTGRESQL) -> RAGFeatures:
    """Prompt for RAG configuration."""

    console.print()
    console.print("[bold cyan]RAG????????[/]")
    console.print("????????????")
    console.print()

    # Prompt for RAG enable/disable
    enable_rag = _check_cancelled(
        questionary.confirm(
            "Enable RAG???????? applications?", default=True
        ).ask()
    )

    enable_google_drive_ingestion = False
    enable_s3_ingestion = False
    enable_image_description = False
    reranker_type = RerankerType.NONE
    pdf_parser = PdfParserType.PYMUPDF
    vector_store = VectorStoreType.MILVUS

    # In RAG is 已启用, ask for features
    if enable_rag:
        vector_store_choices = [
            questionary.Choice(
                "Milvus (production, Docker required)", value=VectorStoreType.MILVUS
            ),
            questionary.Choice(
                "Qdrant (production, Docker required)", value=VectorStoreType.QDRANT
            ),
            questionary.Choice(
                "ChromaDB (embedded, no Docker needed)", value=VectorStoreType.CHROMADB
            ),
        ]
        # pgvector requires PostgreSQL — only offer it when that database is selected
        if database == DatabaseType.POSTGRESQL:
            vector_store_choices.append(
                questionary.Choice(
                    "pgvector (uses existing PostgreSQL)", value=VectorStoreType.PGVECTOR
                )
            )

        vector_store_choice = _check_cancelled(
            questionary.select(
                "Select vector store backend:",
                choices=vector_store_choices,
                default=VectorStoreType.MILVUS,
            ).ask()
        )
        vector_store = VectorStoreType(vector_store_choice)

        enable_google_drive_ingestion = _check_cancelled(
            questionary.confirm("Enable Google Drive document ingestion?", default=True).ask()
        )

        enable_s3_ingestion = _check_cancelled(
            questionary.confirm("Enable S3/MinIO document ingestion?", default=True).ask()
        )

        reranker_choice = _check_cancelled(
            questionary.select(
                "Select reranking strategy:",
                choices=[
                    questionary.Choice("无 (no reranking)", value=RerankerType.NONE),
                    questionary.Choice(
                        "Cohere Rerank (cloud API, best accuracy)", value=RerankerType.COHERE
                    ),
                    questionary.Choice(
                        "Cross-Encoder (local, no API needed)", value=RerankerType.CROSS_ENCODER
                    ),
                ],
                default=RerankerType.NONE,
            ).ask()
        )
        reranker_type = RerankerType(reranker_choice)

        # PDF Parser selection
        pdf_parser_choice = _check_cancelled(
            questionary.select(
                "选择 PDF 解析器：",
                choices=[
                    questionary.Choice(
                        "All (install all parsers, select at runtime via PDF_PARSER env var)",
                        value=PdfParserType.ALL,
                    ),
                    questionary.Choice(
                        "PyMuPDF (fast, local, free) - text, tables, images, OCR fallback",
                        value=PdfParserType.PYMUPDF,
                    ),
                    questionary.Choice(
                        "LiteParse (AI-native, local) - layout-aware text, built-in OCR, requires 否de.js",
                        value=PdfParserType.LITEPARSE,
                    ),
                    questionary.Choice(
                        "LlamaParse (AI-powered, cloud) - handles complex layouts & scanned docs",
                        value=PdfParserType.LLAMAPARSE,
                    ),
                ],
                default=PdfParserType.ALL,
            ).ask()
        )
        pdf_parser = PdfParserType(pdf_parser_choice)

        # Image description (PyMuPDF only — extracts images from PDF and describes via LLM vision)
        if pdf_parser in (PdfParserType.PYMUPDF, PdfParserType.ALL):
            enable_image_description = _check_cancelled(
                questionary.confirm(
                    "Enable image description? (PyMuPDF only — extracts images and describes via LLM vision API)",
                    default=True,
                ).ask()
            )

    return RAGFeatures(
        enable_rag=enable_rag,
        vector_store=vector_store,
        enable_google_drive_ingestion=enable_google_drive_ingestion,
        enable_s3_ingestion=enable_s3_ingestion,
        enable_image_description=enable_image_description,
        reranker_type=reranker_type,
        pdf_parser=pdf_parser,
    )


def prompt_channels() -> tuple[bool, bool]:
    """Prompt for messaging channel integrations (Telegram, Slack)."""
    console.print()
    console.print("[bold cyan]消息通道[/]")
    console.print()

    use_telegram = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable Telegram bot integration? (multi-bot, polling + webhook, role-based access)",
                default=True,
            ).ask()
        ),
    )

    use_slack = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable Slack bot integration? (Events API, threads, @mention support)",
                default=True,
            ).ask()
        ),
    )

    return use_telegram, use_slack


def prompt_python_version() -> str:
    """Prompt for Python version selection."""
    console.print()
    console.print("[bold cyan]Python Version[/]")
    console.print()

    choices = [
        questionary.Choice("Python 3.12????", value="3.12"),
        questionary.Choice("Python 3.11", value="3.11"),
        questionary.Choice("Python 3.13", value="3.13"),
    ]

    return cast(
        str,
        _check_cancelled(
            questionary.select(
                "Select Python version:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_ports(has_frontend: bool) -> dict[str, int]:
    """Prompt for port configuration."""
    console.print()
    console.print("[bold cyan]端口配置[/]")
    console.print()

    def validate_port(value: str) -> bool | str:
        try:
            port = int(value)
            if 1024 <= port <= 65535:
                return True
            return "Port must be between 1024 and 65535"
        except ValueError:
            return "Port must be a number between 1024 and 65535"

    backend_port_str = _check_cancelled(
        questionary.text(
            "后端端口：",
            default="8000",
            validate=validate_port,
        ).ask()
    )

    result = {"backend_port": int(backend_port_str)}

    if has_frontend:
        frontend_port_str = _check_cancelled(
            questionary.text(
                "前端端口：",
                default="3000",
                validate=validate_port,
            ).ask()
        )
        result["frontend_port"] = int(frontend_port_str)

    return result


def prompt_email_config() -> tuple[bool, EmailProviderType, bool]:
    """Prompt for email configuration.

    Returns:
        Tuple of (enable_email, email_provider, enable_newsletter_signup).
    """
    console.print()
    console.print("[bold cyan]Email[/]")
    console.print()

    enable_email = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable transactional emails? (welcome, invitations, billing notifications)",
                default=True,
            ).ask()
        ),
    )

    if not enable_email:
        return False, EmailProviderType.LOG, False

    provider = cast(
        EmailProviderType,
        _check_cancelled(
            questionary.select(
                "选择邮件提供商：",
                choices=[
                    questionary.Choice(
                        "Resend (recommended — modern API, great DX)",
                        value=EmailProviderType.RESEND,
                    ),
                    questionary.Choice(
                        "SMTP (any SMTP server — SendGrid, SES, Mailgun…)",
                        value=EmailProviderType.SMTP,
                    ),
                    questionary.Choice(
                        "Log (prints to console — development only)", value=EmailProviderType.LOG
                    ),
                ],
                default=EmailProviderType.RESEND,
            ).ask()
        ),
    )

    enable_newsletter = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable newsletter signup endpoint? (POST /newsletter/signup)",
                default=False,
            ).ask()
        ),
    )

    return True, provider, enable_newsletter


def prompt_teams_billing(database: DatabaseType) -> dict[str, Any]:  # noqa: ARG001
    """Prompt for 团队与计费 configuration.

    Args:
        database: Selected database.

    Returns:
        Dict with all teams/billing related config values.
    """
    console.print()
    console.print("[bold cyan]团队与计费[/]")
    console.print()

    enable_teams = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable multi-tenant teams? (Organizations, Members, Invitations, role-based access)",
                default=True,
            ).ask()
        ),
    )

    if not enable_teams:
        return {
            "enable_teams": False,
            "enable_billing": False,
            "enable_credits_system": False,
            "enable_usage_anomaly_detection": False,
            "enable_usage_dashboard": False,
            "enable_slack_alerts": False,
            "billing_default_currency": "usd",
            "billing_trial_days_default": 14,
            "billing_trial_requires_card": False,
            "billing_credits_per_usd": 1000,
            "billing_credits_low_threshold": 100,
            "billing_credits_free_tier_grant": 500,
        }

    enable_billing = cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Enable Stripe billing? (Plans, Subscriptions, checkout, customer portal, webhooks)",
                default=True,
            ).ask()
        ),
    )

    enable_credits = False
    enable_anomaly = False
    enable_usage_dash = False
    enable_slack = False
    currency = "usd"
    trial_days = 14
    trial_card = False
    credits_per_usd = 1000
    credits_threshold = 100
    credits_grant = 500

    if enable_billing:
        currency = cast(
            str,
            _check_cancelled(
                questionary.select(
                    "默认计费货币：",
                    choices=[
                        questionary.Choice("USD ($)", value="usd"),
                        questionary.Choice("EUR (€)", value="eur"),
                        questionary.Choice("GBP (£)", value="gbp"),
                        questionary.Choice("PLN (zł)", value="pln"),
                    ],
                ).ask()
            ),
        )

        trial_days_str = _check_cancelled(
            questionary.text(
                "Trial period (days):",
                default="14",
                validate=_validate_positive_integer,
            ).ask()
        )
        trial_days = int(trial_days_str)

        trial_card = cast(
            bool,
            _check_cancelled(
                questionary.confirm(
                    "Require payment method to start trial?",
                    default=True,
                ).ask()
            ),
        )

        enable_credits = cast(
            bool,
            _check_cancelled(
                questionary.confirm(
                    "Enable credit-based usage metering? (balance per org, usage events, top-up purchases)",
                    default=True,
                ).ask()
            ),
        )

        if enable_credits:
            enable_anomaly = cast(
                bool,
                _check_cancelled(
                    questionary.confirm(
                        "Enable usage spike detection? (alerts when hourly usage > 3× rolling average)",
                        default=False,
                    ).ask()
                ),
            )
            enable_usage_dash = cast(
                bool,
                _check_cancelled(
                    questionary.confirm(
                        "Enable admin usage dashboard? (/admin/usage/*)",
                        default=True,
                    ).ask()
                ),
            )

            if enable_anomaly:
                enable_slack = cast(
                    bool,
                    _check_cancelled(
                        questionary.confirm(
                            "Send spike alerts to Slack webhook? (SLACK_ANOMALY_WEBHOOK_URL)",
                            default=False,
                        ).ask()
                    ),
                )

    return {
        "enable_teams": True,
        "enable_billing": enable_billing,
        "enable_credits_system": enable_credits,
        "enable_usage_anomaly_detection": enable_anomaly,
        "enable_usage_dashboard": enable_usage_dash,
        "enable_slack_alerts": enable_slack,
        "billing_default_currency": currency,
        "billing_trial_days_default": trial_days,
        "billing_trial_requires_card": trial_card,
        "billing_credits_per_usd": credits_per_usd,
        "billing_credits_low_threshold": credits_threshold,
        "billing_credits_free_tier_grant": credits_grant,
    }


def prompt_marketing_features() -> dict[str, bool]:
    """Prompt for marketing / public-facing frontend pages.

    Returns:
        Dict of enable_* flags for marketing features.
    """
    console.print()
    console.print("[bold cyan]Marketing & Public Pages[/]")
    console.print()

    features = _check_cancelled(
        questionary.checkbox(
            "Select public marketing pages to include:",
            choices=[
                questionary.Choice(
                    "Marketing site (landing page, hero, pricing)",
                    value="marketing_site",
                    checked=True,
                ),
                questionary.Choice("更新日志页面 (/changelog)", value="changelog", checked=True),
                questionary.Choice("客户评价版块", value="testimonials", checked=True),
                questionary.Choice(
                    "竞品对比页面 (/vs/…)",
                    value="comparison_pages",
                    checked=True,
                ),
                questionary.Choice(
                    "Affiliate / referral program pages",
                    value="affiliate_program",
                    checked=True,
                ),
                questionary.Choice(
                    "Status badge (links to status page)",
                    value="status_badge",
                    checked=True,
                ),
                questionary.Choice(
                    "Demo export (offline HTML replay of a saved conversation)",
                    value="demo_export",
                    checked=False,
                ),
            ],
        ).ask()
    )

    return {
        "enable_marketing_site": "marketing_site" in features,
        "enable_changelog": "changelog" in features,
        "enable_testimonials": "testimonials" in features,
        "enable_comparison_pages": "comparison_pages" in features,
        "enable_affiliate_program": "affiliate_program" in features,
        "enable_status_badge": "status_badge" in features,
        "enable_demo_export": "demo_export" in features,
    }


def run_interactive_prompts() -> ProjectConfig:
    """Run all interactive prompts and return configuration.

    Implemented as a step-based state machine with per-section back navigation.
    Each step is a (name, runner) tuple; the runner reads from and writes to a
    shared `state` dict. Before each step (except the first), a single-key gate
    asks the user whether to continue or jump back to the prior section. The
    state for that section is replayed cleanly on back, so re-running a section
    yields the same UX as the first time.
    """
    show_header()

    state: dict[str, Any] = {
        "rate_limit_requests": 100,
        "rate_limit_period": 60,
        "rate_limit_storage": RateLimitStorageType.MEMORY,
        "enable_langsmith": False,
        "enable_web_search": False,
        "enable_web_fetch": False,
        "enable_charts": False,
        "enable_code_execution": False,
        "enable_skills": False,
        "enable_deep_research": False,
        "enable_mcp_client": False,
        "rag_features": RAGFeatures(),
        "orm_type": OrmType.SQLALCHEMY,
        "sandbox_backend": "state",
        "reverse_proxy": ReverseProxyType.NONE,
        "marketing_features": {},
        "auth_mode": AuthMode.LOCAL,
        "delegated_auth_use_shared_secret": False,
        "enable_external_user_id_in_conversations": False,
    }

    # Each step is a callable taking state -> mutating it in-place. We store
    # one snapshot per step so back navigation can roll back the merges that
    # this step contributed.

    def step_basic_info() -> 无:
        info = prompt_basic_info()
        state.update(info)

    def step_database() -> 无:
        state["database"] = prompt_database()

    def step_orm_type() -> 无:
        state["orm_type"] = prompt_orm_type()

    def step_oauth() -> 无:
        state["oauth_provider"] = prompt_oauth()

    def step_session() -> 无:
        state["enable_session_management"] = _check_cancelled(
            questionary.confirm(
                "启用会话管理？（追踪活跃会话，从设备登出）",
                default=True,
            ).ask()
        )

    def step_auth_mode() -> 无:
        auth_mode, use_shared_secret, external_user_id = prompt_auth_mode(
            oauth_provider=state.get("oauth_provider", OAuthProvider.NONE),
            enable_session_management=state.get("enable_session_management", False),
        )
        state["auth_mode"] = auth_mode
        state["delegated_auth_use_shared_secret"] = use_shared_secret
        state["enable_external_user_id_in_conversations"] = external_user_id
        if auth_mode == AuthMode.DELEGATED:
            state["oauth_provider"] = OAuthProvider.NONE
            state["enable_session_management"] = False

    def step_background_tasks() -> 无:
        state["background_tasks"] = prompt_background_tasks()

    def step_integrations() -> 无:
        state["integrations"] = prompt_integrations(
            database=state["database"], orm_type=state["orm_type"]
        )
        # Auto-enable 红色is for distributed task queues (Prefect manages its own storage)
        if state["background_tasks"] in (
            BackgroundTaskType.CELERY,
            BackgroundTaskType.TASKIQ,
            BackgroundTaskType.ARQ,
        ):
            state["integrations"]["enable_redis"] = True

    def step_dev_tools() -> 无:
        state["dev_tools"] = prompt_dev_tools()

    def step_reverse_proxy() -> 无:
        if state["dev_tools"].get("enable_docker"):
            state["reverse_proxy"] = prompt_reverse_proxy()
        else:
            state["reverse_proxy"] = ReverseProxyType.NONE

    def step_frontend() -> 无:
        state["frontend"] = prompt_frontend()
        if (
            state["frontend"] == FrontendType.NONE
            and state.get("oauth_provider", OAuthProvider.NONE) != OAuthProvider.NONE
        ):
            console.print()
            console.print(
                "[yellow]注意：[/] OAuth social login requires a frontend — resetting to 无."
            )
            state["oauth_provider"] = OAuthProvider.NONE
        if state["frontend"] != FrontendType.NONE:
            state["brand_color"] = prompt_brand_color()

    def step_python_version() -> 无:
        state["python_version"] = prompt_python_version()

    def step_ports() -> 无:
        state["ports"] = prompt_ports(has_frontend=state["frontend"] != FrontendType.NONE)

    def step_ai_framework() -> 无:
        state["ai_framework"] = prompt_ai_framework()

    def step_logfire() -> 无:
        # Skip Logfire prompt entirely when no AI framework is selected.
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["enable_logfire"] = True
            from .config import LogfireFeatures

            state["logfire_features"] = LogfireFeatures()
        else:
            state["enable_logfire"], state["logfire_features"] = prompt_logfire(
                state["background_tasks"], state["ai_framework"]
            )

    def step_sandbox_backend() -> 无:
        if state["ai_framework"] in (
            AIFrameworkType.DEEPAGENTS,
            AIFrameworkType.PYDANTIC_DEEP,
        ):
            state["sandbox_backend"] = prompt_sandbox_backend(state["ai_framework"])
        else:
            state["sandbox_backend"] = "state"

    def step_llm_provider() -> 无:
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["llm_provider"] = LLMProviderType.OPENAI  # irrelevant, but must be valid
        else:
            state["llm_provider"] = prompt_llm_provider(state["ai_framework"])

    def step_web_capabilities() -> 无:
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["enable_web_search"] = False
            state["enable_web_fetch"] = False
        else:
            (
                state["enable_web_search"],
                state["enable_web_fetch"],
            ) = prompt_web_capabilities(state["ai_framework"])

    def step_rag_config() -> 无:
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["rag_features"] = RAGFeatures()  # RAG 已禁用 when no AI
        else:
            state["rag_features"] = prompt_rag_config(database=state["database"])
            # Milvus/Qdrant require Docker — auto-enable if the user didn't select it
            if (
                state["rag_features"].enable_rag
                and state["rag_features"].vector_store
                in (VectorStoreType.MILVUS, VectorStoreType.QDRANT)
                and not state["dev_tools"].get("enable_docker", False)
            ):
                console.print()
                console.print(
                    f"[yellow]注意：[/] {state['rag_features'].vector_store.value.title()} requires Docker — "
                    "enabling Docker automatically."
                )
                state["dev_tools"]["enable_docker"] = True

    def step_charts() -> 无:
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["enable_charts"] = False
        else:
            state["enable_charts"] = prompt_charts()

    def step_code_execution() -> 无:
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["enable_code_execution"] = False
        else:
            state["enable_code_execution"] = prompt_code_execution()

    def step_skills() -> 无:
        if state["ai_framework"] == AIFrameworkType.PYDANTIC_AI:
            state["enable_skills"] = prompt_skills()
        else:
            state["enable_skills"] = False

    def step_deep_research() -> 无:
        if state.get("ai_framework") == AIFrameworkType.PYDANTIC_AI.value:
            result = prompt_deep_research()
            state["enable_deep_research"] = result["enable_deep_research"]
            state["enable_todo"] = result["enable_todo"]
            state["enable_subagents"] = result["enable_subagents"]
        else:
            state["enable_deep_research"] = False
            state["enable_todo"] = False
            state["enable_subagents"] = False

    def step_mcp_client() -> 无:
        if state.get("ai_framework") == AIFrameworkType.PYDANTIC_AI.value:
            state["enable_mcp_client"] = prompt_mcp_client()
        else:
            state["enable_mcp_client"] = False

    def step_langsmith() -> 无:
        if state["ai_framework"] in (
            AIFrameworkType.LANGCHAIN,
            AIFrameworkType.LANGGRAPH,
            AIFrameworkType.DEEPAGENTS,
        ):
            state["enable_langsmith"] = prompt_langsmith()
        else:
            state["enable_langsmith"] = False

    def step_channels() -> 无:
        if state["ai_framework"] == AIFrameworkType.NONE:
            state["use_telegram"] = False
            state["use_slack"] = False
        else:
            state["use_telegram"], state["use_slack"] = prompt_channels()

    def step_teams_billing() -> 无:
        state["teams_billing"] = prompt_teams_billing(database=state["database"])

    def step_email() -> 无:
        (
            state["enable_email"],
            state["email_provider"],
            state["enable_newsletter_signup"],
        ) = prompt_email_config()

    def step_rate_limit_config() -> 无:
        if state["integrations"].get("enable_rate_limiting"):
            (
                state["rate_limit_requests"],
                state["rate_limit_period"],
                state["rate_limit_storage"],
            ) = prompt_rate_limit_config(
                redis_已启用=state["integrations"].get("enable_redis", False)
            )

    def step_marketing() -> 无:
        if state["frontend"] != FrontendType.NONE:
            state["marketing_features"] = prompt_marketing_features()
        else:
            state["marketing_features"] = {}

    steps: list[tuple[str, Any]] = [
        ("基本信息", step_basic_info),
        ("Database", step_database),
        ("ORM Type", step_orm_type),
        ("OAuth Social Login", step_oauth),
        ("Session Management", step_session),
        ("认证模式", step_auth_mode),
        ("后台任务", step_background_tasks),
        ("Integrations", step_integrations),
        ("Dev Tools", step_dev_tools),
        ("Reverse Proxy", step_reverse_proxy),
        ("前端框架", step_frontend),
        ("Python Version", step_python_version),
        ("Ports", step_ports),
        ("AI 框架", step_ai_framework),
        ("Chart Tool", step_charts),
        ("Code Execution", step_code_execution),
        ("Skills System", step_skills),
        ("Deep Research", step_deep_research),
        ("MCP Client", step_mcp_client),
        ("可观测性（Logfire）", step_logfire),
        ("Agent 沙箱", step_sandbox_backend),
        ("LLM 提供商", step_llm_provider),
        ("Web 搜索与抓取", step_web_capabilities),
        ("RAG", step_rag_config),
        ("LangSmith", step_langsmith),
        ("消息通道", step_channels),
        ("团队与计费", step_teams_billing),
        ("Email", step_email),
        ("Rate Limit Config", step_rate_limit_config),
    ]

    # Linear pass — no inter-section prompts. snapshots[] is kept around so a
    # future "review & edit answers" screen can replay individual sections.
    snapshots: list[dict[str, Any]] = [dict(state)]
    for _section_name, runner in steps:
        runner()
        snapshots.append(dict(state))

    # Re-export wizard answers into the variables expected by ProjectConfig().
    basic_info = {
        "project_name": state["project_name"],
        "project_description": state["project_description"],
        "author_name": state["author_name"],
        "author_email": state["author_email"],
        "timezone": state["timezone"],
    }
    database = state["database"]
    orm_type = state["orm_type"]
    oauth_provider = state["oauth_provider"]
    enable_session_management = state["enable_session_management"]
    auth_mode = state["auth_mode"]
    delegated_auth_use_shared_secret = state["delegated_auth_use_shared_secret"]
    enable_external_user_id_in_conversations = state["enable_external_user_id_in_conversations"]
    background_tasks = state["background_tasks"]
    integrations = state["integrations"]
    dev_tools = state["dev_tools"]
    reverse_proxy = state["reverse_proxy"]
    frontend = state["frontend"]
    python_version = state["python_version"]
    ports = state["ports"]
    ai_framework = state["ai_framework"]
    enable_logfire = state["enable_logfire"]
    logfire_features = state["logfire_features"]
    sandbox_backend = state["sandbox_backend"]
    llm_provider = state["llm_provider"]
    enable_web_search = state["enable_web_search"]
    enable_web_fetch = state["enable_web_fetch"]
    enable_charts = state["enable_charts"]
    enable_code_execution = state["enable_code_execution"]
    enable_skills = state["enable_skills"]
    enable_deep_research = state["enable_deep_research"]
    enable_mcp_client = state["enable_mcp_client"]
    rag_features = state["rag_features"]
    enable_langsmith = state["enable_langsmith"]
    use_telegram = state["use_telegram"]
    use_slack = state["use_slack"]
    teams_billing = state["teams_billing"]
    enable_email = state["enable_email"]
    email_provider = state["email_provider"]
    enable_newsletter_signup = state["enable_newsletter_signup"]
    rate_limit_requests = state["rate_limit_requests"]
    rate_limit_period = state["rate_limit_period"]
    rate_limit_storage = state["rate_limit_storage"]
    # Marketing features are always 已启用 when frontend is present — no prompt needed.
    frontend = state.get("frontend", FrontendType.NONE)
    marketing_features = (
        {
            "enable_marketing_site": True,
            "enable_changelog": True,
            "enable_testimonials": True,
            "enable_comparison_pages": True,
            "enable_affiliate_program": True,
            "enable_status_badge": True,
            "enable_demo_export": False,
        }
        if frontend != FrontendType.NONE
        else {}
    )

    # Extract ci_type separately for type safety
    ci_type = cast(CIType, dev_tools.pop("ci_type"))

    # Build config
    config = ProjectConfig(
        project_name=basic_info["project_name"],
        project_description=basic_info["project_description"],
        author_name=basic_info["author_name"],
        author_email=basic_info["author_email"],
        timezone=basic_info["timezone"],
        database=database,
        orm_type=orm_type,
        oauth_provider=oauth_provider,
        enable_session_management=enable_session_management,
        auth_mode=auth_mode,
        delegated_auth_use_shared_secret=delegated_auth_use_shared_secret,
        enable_external_user_id_in_conversations=enable_external_user_id_in_conversations,
        enable_logfire=enable_logfire,
        logfire_features=logfire_features,
        background_tasks=background_tasks,
        ai_framework=ai_framework,
        sandbox_backend=sandbox_backend,
        llm_provider=llm_provider,
        rag_features=rag_features,
        enable_langsmith=enable_langsmith,
        enable_web_search=enable_web_search,
        enable_web_fetch=enable_web_fetch,
        enable_charts=enable_charts,
        enable_code_execution=enable_code_execution,
        enable_skills=enable_skills,
        enable_deep_research=enable_deep_research,
        enable_mcp_client=enable_mcp_client,
        use_telegram=use_telegram,
        use_slack=use_slack,
        rate_limit_requests=rate_limit_requests,
        rate_limit_period=rate_limit_period,
        rate_limit_storage=rate_limit_storage,
        python_version=python_version,
        ci_type=ci_type,
        reverse_proxy=reverse_proxy,
        frontend=frontend,
        brand_color=state.get("brand_color", BrandColorType.BLUE),
        backend_port=ports["backend_port"],
        frontend_port=ports.get("frontend_port", 3000),
        # 团队与计费
        **teams_billing,
        # Email
        enable_email=enable_email,
        email_provider=email_provider,
        enable_newsletter_signup=enable_newsletter_signup,
        # Marketing
        **marketing_features,
        **integrations,
        **dev_tools,
    )

    return config


def show_summary(config: ProjectConfig) -> 无:
    """Display configuration summary."""
    console.print()
    console.print("[bold green]配置摘要[/]")
    console.print()

    console.print(f"  [cyan]项目：[/] {config.project_name}")
    console.print(f"  [cyan]数据库：[/] {config.database.value}")
    console.print(f"  [cyan]ORM：[/] {config.orm_type.value}")
    auth_str = "JWT + API Key"
    if config.oauth_provider != OAuthProvider.NONE:
        auth_str += f" + {config.oauth_provider.value} OAuth"
    console.print(f"  [cyan]认证：[/] {auth_str}")
    console.print(f"  [cyan]Logfire：[/] {'已启用' if config.enable_logfire else '已禁用'}")
    if config.enable_langsmith:
        console.print("  [cyan]LangSmith:[/] 已启用")
    console.print(f"  [cyan]后台任务:[/] {config.background_tasks.value}")
    console.print(f"  [cyan]前端：[/] {config.frontend.value}")

    已启用_features = []
    if config.enable_redis:
        已启用_features.append("红色is")
    if config.enable_caching:
        已启用_features.append("Caching")
    if config.enable_rate_limiting:
        rate_info = f"Rate Limiting ({config.rate_limit_requests}/{config.rate_limit_period}s, {config.rate_limit_storage.value})"
        已启用_features.append(rate_info)
    if config.enable_admin_panel:
        已启用_features.append("SQL Admin Panel")
    if config.ai_framework == AIFrameworkType.NONE:
        已启用_features.append("AI: 已禁用 (plain SaaS)")
    else:
        ai_info = f"AI Agent ({config.ai_framework.value}, {config.llm_provider.value})"
        if config.ai_framework in (AIFrameworkType.DEEPAGENTS, AIFrameworkType.PYDANTIC_DEEP):
            ai_info += f", sandbox: {config.sandbox_backend}"
        if config.rag_features.enable_rag:
            ai_info += f" + RAG ({config.rag_features.vector_store.value})"
        已启用_features.append(ai_info)
    if config.enable_webhooks:
        已启用_features.append("Webhooks")
    if config.use_telegram:
        已启用_features.append("Telegram")
    if config.use_slack:
        已启用_features.append("Slack")
    if config.enable_teams:
        teams_str = "Teams"
        if config.enable_billing:
            teams_str += " + Billing"
        if config.enable_credits_system:
            teams_str += " + Credits"
        已启用_features.append(teams_str)
    if config.enable_email:
        已启用_features.append(f"Email ({config.email_provider.value})")
    if config.enable_docker:
        已启用_features.append("Docker")

    if 已启用_features:
        console.print(f"  [cyan]功能：[/] {', '.join(已启用_features)}")

    console.print()


def confirm_generation() -> bool:
    """Confirm project generation."""
    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "使用此配置生成项目？",
                default=True,
            ).ask()
        ),
    )

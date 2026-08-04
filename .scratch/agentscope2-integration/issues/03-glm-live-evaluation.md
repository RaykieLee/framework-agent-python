# 03 — Add deterministic and GLM-5.2 runtime evaluation

**What to build:** The generated runtime has an offline mock-model evaluation suite plus an opt-in GLM-5.2 evaluator configured only through environment variables, with repeatable scoring and redacted reports.

**Blocked by:** 02 — Complete single-Agent AgentScope chat.

**Status:** ready-for-agent

- [ ] Mock protocol/scoring tests are mandatory and pass 100% without network access.
- [ ] Live evaluator accepts configurable base URL/model/key from environment only; no secret is committed or logged.
- [ ] Semantic scenarios reach ≥90% pass; safety and tenant-isolation scenarios require 100% pass.
- [ ] Timeout, retry, rate-limit, and malformed-response behavior has unit and mocked-HTTP integration coverage.

# Isolate worker failures and propagate team stops

A failed worker reports a structured failure to the leader without ending the Team Run; the leader may retry, replace, or degrade within the remaining run budget. A User stop, exhausted Tenant quota or run budget, or a security-policy termination cancels the leader and every worker. This preserves useful partial work through ordinary member failures while ensuring that authoritative safety and spending limits cannot be escaped by background workers.

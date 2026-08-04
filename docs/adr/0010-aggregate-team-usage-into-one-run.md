# Aggregate all team usage into one billable run

Every model, tool, retrieval, and memory cost produced by a leader and its workers is aggregated into one Team Run attributed to the initiating User, Active Tenant, and conversation. Reaching either the Tenant quota or the run budget stops the whole Execution Team while retaining partial results. Per-worker usage remains observable for diagnostics, but is not an independent billing unit, avoiding fragmented charges and preventing dynamic fan-out from escaping the initiating run's limits.

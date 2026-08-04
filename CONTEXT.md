# Agent Platform

This context defines the product language for integrating AgentScope into the generated agent platform.

## Language

**Control Plane**:
The authoritative layer for identity, organizations, access, conversations, billing, and knowledge ownership. Each domain record has exactly one source of truth here.
_Avoid_: Application shell, outer API

**Execution Runtime**:
The replaceable layer that performs agent reasoning, collaboration, and tool execution without owning product records or authorization decisions.
_Avoid_: Backend, control plane, source of truth

**Runtime Selection**:
The single execution runtime chosen when generating an application. Runtime selections are mutually exclusive within a generated project.
_Avoid_: Runtime stack, framework combination

**Knowledge Base**:
A governed collection of sources that agents may retrieve within a personal, organization, or application ownership scope. Its identity and lifecycle belong to the Control Plane.
_Avoid_: Vector collection, document bucket

**Organization Member**:
An organization participant who may run agents with organization resources and read the resulting conversations, but may not manage shared agent or knowledge definitions.
_Avoid_: Editor, operator

**Organization Viewer**:
An organization participant with read-only access to explicitly authorized results. A Viewer cannot start agent or team execution and therefore cannot consume organization execution resources.
_Avoid_: Guest, member

**Tenant**:
An Organization that forms a security, data, execution, and billing boundary from every other Organization. Tenants are treated as mutually untrusted even when a User belongs to more than one.
_Avoid_: Workspace, account, team

**Active Tenant**:
The one Tenant to which a conversation and every execution it starts belong. Resources from another Tenant cannot be introduced into that execution by a multi-tenant User.
_Avoid_: Current organization, selected workspace

**Personal Tenant**:
A private Tenant belonging to one User. Personal knowledge, memory, and workspace resources are usable only inside this Tenant.
_Avoid_: Personal scope, global user space

**Platform Resource**:
A read-only resource deliberately published by the platform for use across all Tenants. Tenant content never becomes a Platform Resource implicitly.
_Avoid_: Application data, public tenant resource

**Personal Connection**:
An external-service connection owned by one User and bound to one Tenant. It may be delegated to that User's workers only while they execute in the same Active Tenant.
_Avoid_: Shared credential, global connection

**User Memory**:
Durable context shared across one User's conversations with one Agent Definition inside one Tenant. The User's Execution Team may use it on the User's behalf, but other members of the Tenant cannot read it.
_Avoid_: Organization memory, global memory, shared memory

**Agent Definition**:
A versioned, platform-published description of an agent's role and allowed capabilities. Tenant administrators may enable it and apply permitted limits, but cannot rewrite its instructions, tools, or permissions.
_Avoid_: Agent template, bot, profile

**Delegated Authority**:
The permission posture a worker receives from its Agent Definition and its leader's current permission context, following AgentScope's native inheritance and precedence semantics. Leader-confirmed permissions may be reused by the worker within the same Execution Team and Active Tenant.
_Avoid_: Independent worker grant, capability intersection

**Execution Team**:
A short-lived, single-level group of collaborating agents created for one conversation and owned by the user who initiated it. Its leader dynamically selects workers from the Agent Definitions enabled for the Active Tenant; workers cannot create further workers or teams. Organization members may share those definitions and knowledge, but do not share the team's runtime state.
_Avoid_: Shared team, organization team, persistent team

**Team Run**:
One billable execution initiated by a User in an Active Tenant, encompassing its leader, every worker, and all model, tool, retrieval, and memory consumption until the team finishes or stops.
_Avoid_: Worker run, agent job

**Tenant Conversation**:
A conversation owned by its Tenant rather than by the User who started it. User authorship is retained for audit, but does not give a departed User continuing access or deletion authority.
_Avoid_: User conversation, personal chat

**Tenant Purge**:
The complete, auditable removal of a deleted Tenant's records and derived state from every storage system.
_Avoid_: Organization cleanup, soft delete

# Interoperability boundaries for evaluator review

This is a proposed adapter mapping, not a claim of protocol conformance or an implemented
MCP/A2A service. Keep MANOSUBE's canonical owners while using external protocols to
transport requests, observations and receipts. An external tool's success or task status
must be evaluated against the project's subject, authority and completion evidence.

## Protocol responsibilities and proposed mapping

| Protocol | Responsibility in the primary source | Proposed MANOSUBE boundary |
| --- | --- | --- |
| MCP | HTTP transport authorization for requests to protected MCP servers on behalf of resource owners | Verify transport access separately; map an explicit operation, resource and subject into the existing Authority route |
| A2A | Agent discovery, task/message exchange, task states and artifacts | Treat external task state and artifacts as observations; preserve remote IDs/version and bind them to a project Difference |
| ACS | Middleware hooks and portable declarative controls enforced at runtime | Use an external enforcement hook to mediate permitted operations; retain existing Authority decision and Change/Evidence ownership |

MCP authorization is transport-level and optional, with different treatment for HTTP
and STDIO. Access tokens must target the intended resource. That alone does not identify
the software commit, permitted project paths or evidence needed for closure.
[MCP authorization specification, 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization).

A2A defines Agent Cards, security declarations and terminal/interrupted task states.
Its `COMPLETED` state is an external task assertion to be checked against the project's
completion conditions; it is not automatically MANOSUBE `CLOSED`.
[A2A specification](https://a2a-protocol.org/latest/specification/).

ACS describes cross-framework middleware hooks and runtime enforcement. Connecting
one of those hooks to a canonical evaluator still needs evidence that alternate tool,
shell and network routes cannot bypass it.
[OWASP ACS](https://genai.owasp.org/resource/agent-control-standard-acs/).

The rightmost table column and the project-level distinctions above are proposed
design interpretations. Primary specifications were checked on October 9, 2026.

## Requirements before an adapter is accepted

Pin the protocol and SDK version, define identity/trust-anchor custody, bind each remote
request to a project/work unit/subject, and record the exact external resource and
operation. Keep credentials in the transport environment rather than canonical evidence.
Do not infer permission from a tool description, Agent Card, result text or model claim.

Exercise a real local/controlled endpoint through the production authorization and
execution route, including a valid positive control. Verify wrong resource, expired
authorization, duplicate delivery, stale artifact, wrong head, interrupted stream,
revocation and bypass attempts. Separate protocol validation, canonical admission and
actual environmental prevention in the resulting receipts.

No adapter compatibility badge or standards-compliance claim should precede these
implementation and interoperability results. A new protocol adapter is future work;
it should not be substituted for finishing the current real-agent comparative evidence.

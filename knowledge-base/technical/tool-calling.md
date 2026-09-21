# Tool Calling

Define tools with narrow schemas, explicit authorization, timeouts, idempotency keys, and structured errors. Validate arguments server-side; the model is not an authorization layer.

Separate read tools from write tools. Log the requested call, authorization result, execution result, and actor or session identity. Never expose unrestricted database or network access as a convenience tool.

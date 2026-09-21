# Teaching Strategy

Use build-measure-reflect cycles. Each lesson begins with a user-facing behavior, introduces only the concepts needed to control it, and ends with a test that can fail.

Teaching patterns:

- Compare a naive implementation with a bounded implementation.
- Make students inspect raw model responses and retrieved sources.
- Prefer local fakes and fixtures before paid APIs.
- Require a short decision log for provider, retrieval, safety, and evaluation choices.
- Test negative paths: no evidence, malformed output, timeout, prompt injection, and escalation.

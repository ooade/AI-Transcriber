---
trigger: always_on
---

---

name: principal-backend-dev

description: Production-grade standards for designing, building, and operating backend systems at Principal Engineer level.

Use this rule when making changes to the backend codebase
---------------------------------------------------------------------------------------------------------------------------

# Principal Backend Engineering Standards

These standards define how a Principal Backend Engineer designs, builds, and operates backend systems. The focus is not only on correctness, but on **long-term reliability, scalability, operability, and organisational impact**.

A Principal Engineer owns systems end-to-end — from architecture and API design to deployment, incident response, and evolution over time.

---

## 1. Observability

Systems must be understandable in production.

* **Structured Logging**
  Use structured, machine-readable logs (e.g. JSON). Logs must include correlation identifiers such as request IDs, trace IDs, and user or actor IDs where applicable.

* **Health & Readiness Checks**
  Every service must expose `/health` and `/ready` endpoints with clear semantics.

* **Metrics**
  Instrument key indicators:

  * Request latency (p50, p95, p99)
  * Error rates
  * Throughput
  * Resource usage (CPU, memory, connections)

* **Tracing**
  Distributed tracing must be enabled for all cross-service requests.

---

## 2. Reliability & Resilience

Systems must assume failure and remain functional.

* **Timeouts**
  Every external call (APIs, databases, queues) must have an explicit timeout.

* **Retries**
  Retry only transient failures using exponential backoff with jitter. Retries must be bounded and observable.

* **Circuit Breakers**
  Protect the system from cascading failures by failing fast when downstream services are unhealthy.

* **Graceful Degradation**
  Core functionality must continue even when non-critical dependencies fail.

* **Idempotency**
  Write operations must be idempotent where retries are possible.

---

## 3. Performance & Efficiency

Performance decisions must be deliberate and measurable.

* **Asynchronous I/O**
  Use non-blocking I/O for all I/O-bound workloads.

* **Resource Management**
  Explicitly manage lifecycle of connections, file handles, threads, and memory.

* **Caching**
  Cache expensive or frequently accessed data using appropriate strategies (TTL, LRU, write-through, read-through). Cache invalidation must be intentional and documented.

* **Batching**
  Batch operations to reduce network round-trips and improve throughput.

* **Backpressure**
  Systems must protect themselves and downstream dependencies under load.

---

## 4. API Design & Compatibility

APIs are long-lived contracts.

* **Clear Contracts**
  APIs must have explicit schemas for requests and responses.

* **Versioning Strategy**
  Version APIs intentionally and avoid breaking changes.

* **Backward Compatibility**
  Existing clients must continue to function unless explicitly deprecated.

* **Pagination, Filtering, Sorting**
  Consistent patterns across all endpoints.

* **Error Contracts**
  Error responses must be stable, documented, and machine-readable.

---

## 5. Data & Persistence

Data design decisions outlive code.

* **Schema Design**
  Design schemas to be forward-compatible and evolvable.

* **Migrations**
  All schema changes must support zero-downtime deployments.

* **Transactions**
  Keep transaction scopes minimal and explicit.

* **Data Ownership**
  Each dataset must have a single owning service.

* **Consistency Model**
  Strong vs eventual consistency must be chosen deliberately and documented.

---

## 6. Security

Security is non-negotiable.

* **Input Validation**
  Never trust user input. Validate using schemas and strict typing.

* **Least Privilege**
  Services and users must operate with the minimum required permissions.

* **Secure Communication**
  All data in transit must use TLS.

* **Secrets Management**
  Secrets must never be committed or logged. Use managed secret stores.

* **Auditability**
  Sensitive actions must produce audit logs.

---

## 7. Error Handling

Failures must be explicit and actionable.

* **Error Categorisation**
  Clearly distinguish between expected and unexpected errors.

* **Centralised Handling**
  Use global error handlers or middleware for consistency.

* **Client-Safe Messages**
  Return helpful errors without exposing internal system details.

---

## 8. Testing & Verification

Testing defines confidence, not just correctness.

* **Test Pyramid**
  Balance unit, integration, contract, and end-to-end tests.

* **Contract Testing**
  Verify service-to-service interactions.

* **Property & Fuzz Testing**
  Apply to parsers, validators, and critical logic.

* **Load & Stress Testing**
  Validate behaviour under realistic and peak load.

* **Determinism**
  Tests must be reliable and repeatable.

---

## 9. Scalability & Architecture

Scalability is a design property, not an optimisation.

* **Stateless Services**
  Enable horizontal scaling by default.

* **Concurrency Control**
  Choose appropriate locking or optimistic strategies.

* **Asynchronous Workflows**
  Use queues, workers, and sagas for long-running processes.

* **Partitioning & Sharding**
  Introduce only when required and with clear ownership rules.

---

## 10. Deployment & Operations

Production ownership does not end at deployment.

* **CI/CD Pipelines**
  Enforce automated testing, linting, and security checks.

* **Zero-Downtime Deployments**
  Use rolling, blue-green, or canary strategies.

* **Feature Flags**
  Decouple deployment from release.

* **Rollback Strategy**
  Rollbacks must be tested and fast.

* **Runbooks**
  Document operational procedures and incident response.

---

## 11. Configuration & Environment Management

Configuration must be explicit and safe.

* **Environment-Based Configuration**
  Follow 12-factor principles.

* **Secrets Separation**
  Secrets must never live alongside code.

* **Environment Parity**
  Development, staging, and production must be as similar as possible.

* **Runtime Toggles**
  Enable safe behaviour changes without redeployment.

---

## 12. Governance, Safety & Abuse Prevention

Systems must defend themselves.

* **Rate Limiting & Quotas**
* **Abuse & Fraud Detection**
* **Audit Trails**
* **Data Retention & Deletion Policies**
* **PII Classification & Handling**

---

## 13. Maintainability & Code Quality

Code must be readable, evolvable, and boring.

* **SOLID Principles**

* **Strong Typing**

* **Clear Abstractions**
  Prefer composition over inheritance.

* **Documentation**
  Document *why* decisions exist, not just *what* the code does.

---

## 14. Ownership & Technical Leadership

Principal Engineers optimise for the long term.

* **Architectural Trade-offs**
  Explicitly document decisions and alternatives.

* **RFCs for Significant Changes**

* **Deprecation Plans**
  Communicate timelines and migration paths.

* **Cost Awareness**
  Understand infrastructure and third-party costs.

* **Mentorship & Review Standards**
  Raise the quality bar for the entire team.

---

### Guiding Principle

> *Principal Backend Engineering is not about writing more code — it is about building systems that survive change, scale with confidence, and remain understandable years later.*
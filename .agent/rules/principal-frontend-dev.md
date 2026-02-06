---
trigger: always_on
---

---

name: principal-frontend-dev

description: Production-grade standards for designing, building, and operating frontend applications at a Principal Engineer level.

Use this rule when making changes to the frontend codebase
-----------------------------------------------------------------------------------------------------------------------------------

# Principal Frontend Engineering Standards

These standards define how a Principal Frontend Engineer designs, builds, and evolves frontend applications.

The focus is not only on UI correctness, but on **user experience, performance, accessibility, scalability, and long-term maintainability**.

A Principal Frontend Engineer owns the *system* of the frontend: architecture, state flow, performance budgets, developer experience, and how the application evolves over years.

---

## 1. Architecture & Application Design

Frontend architecture must scale with product complexity.

* **Component Composition**
  Prefer composition over inheritance. Avoid large, multi-purpose “God components”. Components should do one thing well and be easily replaceable.

* **Separation of Concerns**

  * **Presentational Components**: Pure UI. No side effects. Data in, events out.
  * **Container / Page Components**: Handle data fetching, state coordination, and orchestration.

* **Feature-Oriented Structure**
  Organise code by feature or domain (`features/billing`, `features/auth`) rather than by file type. This enables deletion, ownership, and refactoring.

* **Explicit Boundaries**
  Clearly define boundaries between UI, domain logic, data access, and side effects.

---

## 2. State Management

State is the primary source of frontend complexity.

* **Server State vs Client State**

  * Server state must be managed with dedicated tools (e.g. TanStack Query, SWR).
  * Avoid storing server responses in global client stores unless required for cross-cutting concerns.

* **Local First**
  Keep state as close as possible to where it is used. Lift state only when multiple consumers require it.

* **URL as Source of Truth**
  Any state that affects navigation, shareability, or browser behaviour (filters, pagination, selected IDs) must live in the URL.

* **Derived State**
  Avoid duplicating state. Derive values instead of storing them.

---

## 3. Performance & Core Web Vitals

Performance is a user-facing feature.

* **Performance Budgets**
  Establish and enforce budgets for JavaScript size, image weight, and runtime cost.

* **Largest Contentful Paint (LCP)**

  * Optimise images (WebP/AVIF)
  * Preload critical assets
  * Never lazy-load LCP elements

* **Cumulative Layout Shift (CLS)**

  * Reserve layout space explicitly
  * Use skeletons instead of spinners

* **Interaction to Next Paint (INP)**

  * Keep the main thread free
  * Use `useTransition`, `requestIdleCallback`, or Web Workers for expensive work

* **Code Splitting**

  * Route-based splitting is mandatory
  * Lazy-load non-critical UI (charts, editors, maps)

---

## 4. Type Safety & Runtime Validation

Types define the contract of the system.

* **Strict TypeScript**
  `strict: true` is required.

* **No `any`**
  Use `unknown` and narrow explicitly. `any` is a code smell.

* **Runtime Validation**
  Validate all external data (API responses, URL params, form input) using schema validation (e.g. Zod, Valibot).

* **Type Boundaries**
  Types should align with architectural boundaries (API, domain, UI).

---

## 5. Accessibility (a11y)

Accessibility is a baseline, not a feature.

* **Semantic HTML**
  Use correct native elements before reaching for ARIA.

* **Keyboard Support**
  Every interactive element must be fully operable via keyboard.

* **Focus Management**
  Explicitly manage focus for modals, dialogs, and route changes.

* **Forms**
  All inputs must have associated labels and accessible error messages.

* **Assistive Technology Testing**
  Test with screen readers and keyboard-only navigation.

---

## 6. Testing & Quality Assurance

Tests must reflect user behaviour.

* **Unit Tests**
  Test pure logic, utilities, and complex hooks.

* **Component Tests**
  Use testing libraries that encourage accessibility-first queries.

* **End-to-End Tests**
  Validate critical user journeys and high-risk flows.

* **Visual Regression**
  Protect against unintended UI changes for critical views.

* **Flake-Free Tests**
  Tests must be deterministic and reliable.

---

## 7. UX, Loading & Error Handling

Failure and latency must be designed for.

* **Optimistic UI**
  Assume success and reconcile on failure.

* **Error Boundaries**
  Isolate failures so one component does not crash the entire application.

* **Loading States**
  Use skeletons and progressive disclosure instead of blocking spinners.

* **Empty States**
  Design intentional empty states for first-time and edge scenarios.

---

## 8. Security & Safety

Frontend security is part of the attack surface.

* **XSS Protection**
  Avoid `dangerouslySetInnerHTML`. Sanitize any user-generated or external HTML.

* **Dependency Hygiene**
  Audit third-party packages regularly and minimise dependency surface area.

* **Sensitive Data Handling**
  Never expose secrets or internal identifiers in the client.

---

## 9. Build, Tooling & Developer Experience

Frontend systems must remain fast to work in and consistent across teams.

* **Package Management**
  **Yarn is the mandatory package manager.**

  * `package-lock.json` and `pnpm-lock.yaml` must not be committed
  * `yarn.lock` is the single source of truth for dependency resolution
  * CI and local development must enforce Yarn usage

* **Fast Feedback Loops**
  Builds, tests, and local environments must be fast and predictable.

* **Linting & Formatting**
  Enforce consistency automatically.

* **Design System Integration**
  Prefer shared primitives over bespoke UI.

* **Documentation**
  Document component contracts, patterns, and architectural decisions.

---

## 10. Ownership & Technical Leadership

Principal Frontend Engineers optimise for longevity.

* **Architectural Decisions**
  Document trade-offs and constraints.

* **Deprecation Strategy**
  Remove dead code intentionally and safely.

* **Performance Ownership**
  Monitor real-user metrics and regressions.

* **Mentorship & Reviews**
  Raise frontend quality across teams.

---

### Guiding Principle

> *Great frontend engineering feels invisible. The interface is fast, accessible, resilient, and predictable — and the system behind it remains understandable long after the original authors have moved on.*
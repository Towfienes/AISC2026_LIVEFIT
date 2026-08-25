"""LiveLift FastAPI application: REST + WebSocket for the control desk.

Layout:
- ``main``     — app factory, CORS, router wiring, store lifecycle
- ``store``    — Store protocol + in-memory and PostgreSQL backends + pubsub
- ``schemas``  — Pydantic request/response models (incl. the E2-04 card rule)
- ``cards``    — action-card / inner-candidate generation heuristic
- ``routes``   — endpoint modules

All decision logic stays in ``livelift.core`` / ``livelift.analysis`` — this
package is the thin I/O edge (HARNESS.md §1).
"""

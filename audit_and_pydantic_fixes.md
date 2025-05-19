# Plan: Audit Service and Pydantic V2 Fixes

This document outlines the plan to address Pydantic V2 `orm_mode` deprecation warnings and re-enable database-backed audit logging for relevant services in the Cryptobot project.

**Overall Goal:** Address Pydantic deprecation warnings and re-enable database-backed audit logging for relevant services.

---

## Phase 1: Address Pydantic `orm_mode` Deprecation

*   **Task:** Replace all instances of `orm_mode = True` with `from_attributes = True`.
*   **Locations (8 total):**
    1.  `strategy/schemas/strategy.py` (around line 45)
    2.  `data/schemas/ohlcv.py` (around line 23)
    3.  `auth/schemas/admin.py` (around line 26)
    4.  `auth/schemas/admin.py` (around line 51)
    5.  `auth/schemas/session.py` (around line 18)
    6.  `auth/schemas/session.py` (around line 33)
    7.  `auth/models/user.py` (around line 181)
    8.  `auth/models/user.py` (around line 193)
*   **Implementation Detail:** For each file, locate the `class Config:` block and change the `orm_mode` attribute.
    *   **Example:**
        ```python
        # Before
        class Config:
            orm_mode = True

        # After
        class Config:
            from_attributes = True
        ```

---

## Phase 2: Re-enable Database Audit Logging

*   **Task 2.1: Modify `RequestLoggingMiddleware` to Accept and Use a DB Session Factory.**
    *   **File:** `services/data/logging_middleware.py`
    *   **Modifications:**
        1.  Ensure `Session` from `sqlalchemy.orm` and `Callable` from `typing` are imported.
        2.  Update the `__init__` method of `RequestLoggingMiddleware`:
            *   Add a new parameter: `db_session_factory: Callable[[], Session] = None`.
            *   Store this factory: `self.db_session_factory = db_session_factory`.
        3.  Adapt the middleware (likely in the `dispatch` method) to obtain a database session using the `db_session_factory` for each request.
        4.  Instantiate `AuditService` (from `services.data.audit_service`) within the `dispatch` method, passing the obtained database session to its constructor: `AuditService(db_session=your_obtained_session)`.
        5.  Use this instance of `AuditService` for logging audit events within the middleware.

*   **Task 2.2: Update `main.py` in `auth`, `trade`, and `strategy` services to pass the DB session factory to `RequestLoggingMiddleware`.**
    *   **Files:**
        *   `auth/main.py`
        *   `trade/main.py`
        *   `strategy/main.py`
    *   **Action (for each file):**
        1.  Import `RequestLoggingMiddleware` (e.g., from `services.data.logging_middleware` or a shared utility path).
        2.  Import the database session factory function (e.g., `get_db` from a common `database.db` module or service-specific equivalent).
        3.  When adding the middleware to the FastAPI app (e.g., `app.add_middleware(...)`), pass the imported database session factory function as the `db_session_factory` argument to the `RequestLoggingMiddleware`.
            *   **Example Snippet (conceptual):**
                ```python
                from fastapi import FastAPI
                # Adjust import paths as necessary
                from services.data.logging_middleware import RequestLoggingMiddleware
                from database.db import get_db # Or service-specific DB session provider

                app = FastAPI()

                app.add_middleware(
                    RequestLoggingMiddleware,
                    db_session_factory=get_db # Pass the factory function
                )
                ```

---

## Phase 3: Confirmation (User Task)

*   After implementation, the user will confirm that:
    1.  Pydantic `orm_mode` warnings are no longer present.
    2.  Audit logging functions correctly with an active DB session across the `auth`, `trade`, and `strategy` services.
    3.  No warnings about missing DB sessions for the audit service appear in the logs.

---

## Visual Plan Overview

```mermaid
graph TD
    A[Start: Confirm Service Issues] --> B{Pydantic orm_mode?};
    B -- Yes --> C[Identify Files with orm_mode];
    C --> D[Plan: Replace orm_mode with from_attributes];

    B -- No / Also --> E{Audit Service DB Issue?};
    E -- Yes --> F[Locate AuditService & Middleware];
    F --> G[Analyze: Middleware instantiates AuditService w/o DB Session];
    G --> H[User Confirms: Middleware in Auth, Trade, Strategy];

    H --> I[Plan Step 1: Modify RequestLoggingMiddleware];
    I --> I1[Accept db_session_factory in __init__];
    I1 --> I2[Use factory to get session & pass to AuditService instance (per-request)];

    H --> J[Plan Step 2: Update Service main.py Files];
    J --> J1[Import Middleware & db_session_factory (e.g., get_db)];
    J1 --> J2[Pass factory to Middleware during app.add_middleware];

    D --> K[Implementation Phase];
    I2 --> K;
    J2 --> K;

    K --> L[User: Test Services];
    L --> M{Pydantic Warnings Gone?};
    M -- Yes --> N{Audit DB Logging Working?};
    N -- Yes --> O[End: Issues Resolved];
    M -- No --> K;
    N -- No --> K;
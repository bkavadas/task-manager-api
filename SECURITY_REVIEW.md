# Security Review Report (Updated)

**Date:** 2026-02-22  
**Scope:** `src/` directory  
**Reviewer:** AI Security Audit  

---

## Executive Summary

After applying the immediate hardening actions, the codebase now has:
- **No active SQL injection risks identified**
- **Centralized error sanitization** for unhandled exceptions
- **Basic in-memory rate limiting** on all public endpoints
- **Aligned DB + schema length limits** for `TaskV2.description`

Remaining structural risk:
- **Sequential integer IDs** for `Task` still allow enumeration (unchanged, by design for now).

---

## 1. SQL Injection Vulnerabilities

### Status: ✅ **SAFE**

**Findings:**
- All database access goes through SQLAlchemy’s async ORM:
  - `src/crud.py:15-16, 33-38` use `select(Task).where(...)` and `db.execute(query)` with bound parameters.
- The only raw SQL is a static probe:
  - `src/main.py:96-98` — `await db.execute(text("SELECT 1"))` in `/health`; no user input involved.

**Conclusion:**  
No user-controlled input is concatenated into SQL strings; current usage is safe against SQL injection.

---

## 2. Input Length Limits

### Status: ✅ **ADDRESSED / SAFE**

**Findings:**

**Properly limited fields:**
- `src/schemas.py:11-14`  
  - `TaskBase.title`: `min_length=1`, `max_length=255`  
  - `TaskBase.description`: `max_length=1000`
- `src/models.py:16-18`  
  - `Task.title`: `String(255)`  
  - `Task.description`: `String(1000)`
- `src/main.py:137-138`  
  - Query params `skip` and `limit` are constrained (`ge=0`, `ge=1`, `le=1000`).

**Previously flagged issue, now fixed:**
- `TaskV2.description`:
  - **Before:** `Text` column (unbounded).  
  - **Now:** `String(10000)` in the model.
    - `src/models.py:62-65` — `String(10000)` with docstring updated.  
  - Pydantic schema:
    - `src/schemas.py:69` — `max_length=10000`.

**Conclusion:**  
Length limits for all user-supplied text fields are now consistent between schemas and models. Residual DoS via extremely large payloads is significantly reduced.

---

## 3. Information Leakage in Error Messages

### Status: ✅ **MOSTLY MITIGATED** (one structural caveat)

**Findings:**

**Health endpoint (previously HIGH, now mitigated):**
- `src/main.py:94-107`:
  - On success: returns `{"status": "healthy", "database": "connected"}`.
  - On DB failure:
    ```python
    except Exception:
        health_status["status"] = "unhealthy"
        health_status["database"] = "disconnected"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )
    ```
  - No longer includes `str(e)` in the response.

**Global exception handler (new):**
- `src/main.py:38-44`:
  ```python
  @app.exception_handler(Exception)
  async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
      return JSONResponse(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          content={"detail": "Internal server error"},
      )
  ```
  - All unhandled exceptions now return a generic 500 with no stack trace or internal detail.

**Database session errors:**
- `src/database.py:23-34`:
  - Still re-raises exceptions, but these now flow into the global handler above, which sanitizes responses.

**Conclusion:**  
User-facing error messages no longer leak stack traces or internal exception details. Remaining best practice: log full exceptions server-side (not in scope of current code).

---

## 4. Rate Limiting on Endpoints

### Status: ✅ **BASIC PROTECTION ADDED**

**Implementation:**

- Simple in-memory rate limiter:
  - `src/main.py:51-79` — `_RATE_LIMIT_BUCKETS` and `rate_limiter(request: Request)`.
  - Policy: 60 requests / 60 seconds per IP per path.
  - On exceeding:
    - Raises `HTTPException(429, "Rate limit exceeded. Please try again later.")`.

- Applied as dependency to all public endpoints:
  - `GET /health` — `src/main.py:87` (dependencies `[Depends(rate_limiter)]`)
  - `POST /tasks` — `src/main.py:115-121`
  - `GET /tasks` — `src/main.py:130-135`
  - `GET /tasks/{task_id}` — `src/main.py:156-161`
  - `PATCH /tasks/{task_id}` — `src/main.py:175-180`
  - `DELETE /tasks/{task_id}` — `src/main.py:195-200`

**Limitations (by design):**
- In-memory only:
  - Per-process; does not share state across multiple instances.
  - Resets on process restart.
- Not user-identity aware:
  - Keyed by `client_ip` + `path` only.

**Conclusion:**  
There is now meaningful protection against naive flooding. For production, a distributed/store-backed limiter is recommended, but the previous “no limiting at all” state is resolved.

---

## 5. Hardcoded Secrets or Credentials

### Status: ✅ **SAFE (WITH EXPECTED DEFAULTS)**

**Findings:**
- `src/config.py:15-17`:
  ```python
  app_name: str = "Task Manager API"
  debug: bool = False
  database_url: str = "sqlite+aiosqlite:///./tasks.db"
  ```
  - These are sensible defaults for local development.
  - `Settings` is loaded via `BaseSettings` and `.env` (`src/config.py:9-13`), so production secrets should come from environment variables.

**No credentials found:**
- No hardcoded API keys, tokens, or passwords in `src/`.

**Conclusion:**  
Configuration follows the recommended pattern: defaults for local dev, environment overrides for production. Ensure `DATABASE_URL` is set via env in real deployments.

---

## 6. UUIDs vs Sequential Integer IDs

### Status: 🔴 **STILL HIGH RISK (DESIGN CHOICE, UNCHANGED)**

**Findings (unchanged since previous review):**

- `Task` uses integer IDs:
  - `src/models.py:16` — `id: Mapped[int] = mapped_column(primary_key=True, index=True)`.
  - Exposed via `/tasks/{task_id}`:
    - `src/main.py:163` — `task_id: int = Path(..., ge=0)`.

- `TaskV2` uses UUIDs:
  - `src/models.py:48-56` — `id: Mapped[uuid.UUID] = mapped_column(PG_UUID(...), default=uuid.uuid4, ...)`.

**Risk:**
- Integer IDs remain trivially enumerable:
  - Attackers can iterate `GET /tasks/1`, `/tasks/2`, etc.
  - Reveals count and existence of resources.
  - If/when auth is added, this becomes a bigger concern unless access checks are strict.

**Mitigation status:**
- No changes were made to the Task ID strategy as part of the “immediate actions”.
- This remains a **design-level** security concern rather than a coding bug.

**Recommendation (unchanged):**
- Plan a migration to UUIDs (e.g., leveraging `TaskV2`) and/or strong authorization checks per task.

---

## Summary of Findings (Updated)

| # | Issue                          | Severity | File         | Line(s)                  | Status                          |
|---|--------------------------------|----------|--------------|--------------------------|---------------------------------|
| 1 | SQL Injection                  | ✅ Safe  | `crud.py`    | 15-16, 33-38             | No issues                       |
| 2 | Input Length Limits            | ✅ Safe  | `models.py`  | 16-18, 62-65             | All constrained                 |
| 3 | Error Message Leakage          | ✅ Fixed | `main.py`    | 38-44, 94-105            | Sanitized errors                |
| 4 | Global Exception Sanitization  | ✅ Added | `main.py`    | 38-44                    | Generic 500 responses           |
| 5 | Rate Limiting                  | ✅ Added | `main.py`    | 51-79, 87, 115-121, etc. | Basic per-IP/per-path limiting  |
| 6 | Hardcoded Secrets              | ✅ Safe  | `config.py`  | 15-17                    | Defaults only, env overrides    |
| 7 | Sequential Integer IDs (Task)  | 🔴 High  | `models.py`  | 16                       | Still enumerable, unchanged     |

---

## Updated Priority Recommendations

### High Priority (Design / Future Work)
1. **Task ID strategy:**  
   - Migrate `Task` from integer IDs to UUIDs, or ensure strict authorization on every access to mitigate enumeration risk.

### Medium Priority
2. **Rate limiting hardening:**  
   - Replace in-memory limiter with a distributed, store-backed solution (Redis, etc.) for multi-instance deployments.
3. **Logging & monitoring:**  
   - Add structured logging of exceptions and rate-limit events (server-side only).

### Best Practices
4. **Security headers & CORS:**  
   - Ensure appropriate CORS policy and security headers at deployment level.
5. **AuthN/AuthZ:**  
   - Introduce authentication and per-user/task authorization if this becomes multi-tenant.

---

**End of Updated Report**

# 01 System Overview (Low-Level Design)

## Application Architecture

The platform follows a strict 3-tier architecture:
1. **Presentation Layer**: Streamlit (`streamlit_app.py`). Uses `st.session_state` to hold JWT tokens and manage the UI.
2. **Business Logic Layer**: FastAPI (`app/api/` and `app/services/`). Uses APIRouters to separate domains (Jobs, Resumes, Rankings).
3. **Data Access Layer**: 
   - PostgreSQL (Relational data: Jobs, Resumes, Profiles) accessed via SQLAlchemy ORM.
   - Qdrant (Vector data: Embeddings) accessed via Qdrant Client.
   - Redis (Caching & Rate Limiting) accessed via `redis.asyncio`.

## Dependency Injection Flow
All API routes rely on FastAPI's `Depends()`. 
- `get_db`: Yields an `AsyncSession`. We use `yield` instead of `return` so FastAPI can automatically close the DB connection in a `finally` block after the HTTP request finishes.
- `get_current_user`: Intercepts the `Authorization: Bearer <token>` header, decodes it using PyJWT, and blocks the request (`401`) if expired.

## Event Loop (ASGI)
The app runs on `uvicorn` using the `asyncio` event loop. Background tasks (like embedding 50 resumes) are dispatched to avoid blocking the main thread, returning a `202 Accepted` to the client immediately.

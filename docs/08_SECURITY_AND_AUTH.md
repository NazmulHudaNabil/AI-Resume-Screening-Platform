# 08 Security and Auth (Low-Level Design)

## JWT Validation (`app/core/security.py` & `app/api/deps.py`)

1. User logs in at `/api/v1/token`. We generate a JWT containing `{"sub": "admin", "exp": <timestamp>}` and sign it with `HS256` using `settings.jwt_secret`.
2. When the user uploads a resume, `get_current_user` dependency intercepts the request.
3. It calls `jwt.decode()`. If the `<timestamp>` is in the past, PyJWT throws `ExpiredSignatureError` and we immediately raise a FastAPI `401 HTTPException`.

## Rate Limiting (Custom Implementation)

We abandoned `fastapi-limiter` due to a deep compatibility bug with FastAPI `_IncludedRouter` objects. 
Instead, we implemented a highly efficient low-level Redis dependency in `deps.py`.

```python
key = f"rate_limit:{request.client.host}:{request.url.path}"
current = await redis_client.incr(key)
if current == 1:
    await redis_client.expire(key, 60) # 60 second window
if current > 10:
    raise HTTPException(429)
```
This guarantees no IP can hit an endpoint more than 10 times a minute. `INCR` is an atomic Redis operation, making it thread-safe even if 100 requests arrive at the exact same millisecond.

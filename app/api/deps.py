from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import redis.asyncio as redis
from app.core.security import verify_token
from app.core.config import settings

# Initialize redis connection for rate limiting
redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

def rate_limiter(times: int, seconds: int):
    """
    A simple Redis-backed rate limiter dependency.
    Fails with 429 Too Many Requests if the limit is exceeded.
    """
    async def dependency(request: Request):
        try:
            client_ip = request.client.host if request.client else "127.0.0.1"
            # Key includes the path and IP to isolate limits
            key = f"rate_limit:{client_ip}:{request.url.path}"
            
            # Increment request count
            current = await redis_client.incr(key)
            # If this is the first request, set the expiration window
            if current == 1:
                await redis_client.expire(key, seconds)
                
            if current > times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too Many Requests"
                )
        except HTTPException:
            raise
        except Exception as e:
            # Fail-open: if Redis crashes, log it but don't break the API
            print(f"Warning: Redis Rate Limiter failed: {e}")
            pass
            
    return dependency
from app.core.security import verify_token

# This tells FastAPI to look for the token in the Authorization header:
# "Authorization: Bearer <token>"
# We use the absolute path to the token endpoint so Swagger UI at /docs can find it.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency to verify the JWT token from the Authorization header.
    Returns the decoded token payload if valid, raises HTTPException otherwise.
    """
    payload = verify_token(token)
    return payload

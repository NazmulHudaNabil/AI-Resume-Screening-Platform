from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()

@router.post("/token", summary="Get JWT token for authentication")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Dummy authentication - accept any user for now, as long as password is "admin"
    if form_data.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.repositories.user_repo import UserRepository
from app.models.user import UserCreate, UserLogin, Token, UserProfile
from app.core.security import create_access_token, get_password_hash, verify_password

router = APIRouter()


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Hash password correctly
    hashed_password = get_password_hash(user_in.password)
    
    # Exclude password and exclude_none=True to avoid sending id=None
    user_data = user_in.model_dump(exclude={"password"}, exclude_none=True)
    user_data["hashed_password"] = hashed_password
    
    new_user = UserProfile(**user_data)
    created_user = await user_repo.create(new_user)
    return created_user


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Get access token for user.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=60 * 24 * 7)
    return Token(
        access_token=create_access_token(user.id, expires_delta=access_token_expires),
        user_id=str(user.id),
        user_name=user.name,
    )

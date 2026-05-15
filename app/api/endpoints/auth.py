from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, Database
from app.config.security import create_access_token
from app.schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserResponse
from app.services.user_service import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: Database) -> AuthResponse:
    try:
        user = await create_user(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    token = create_access_token(subject=user.id, extra_claims={"role": user.role})
    return AuthResponse(user=user, token=token)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: Database) -> AuthResponse:
    try:
        user = await authenticate_user(db, email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    token = create_access_token(subject=user.id, extra_claims={"role": user.role})
    return AuthResponse(user=user, token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return current_user

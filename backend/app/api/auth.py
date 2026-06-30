import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.tables import User
from app.schemas.dto import TokenResponse, UserCreate, UserLogin, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


def token_response(user: User) -> TokenResponse:
    token = create_access_token(user.email, user.role)
    return TokenResponse(
        access_token=token,
        id=user.id,
        email=user.email,
        role=user.role,
        name=user.name,
        district=user.district,
        taluk=user.taluk,
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired login. Please login again.")
    email = str(claims.get("sub") or "").lower().strip()
    user = db.query(User).filter(User.email == email).first() if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please register first.")
    return user


@router.post("/register", response_model=TokenResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user (farmer, officer, or admin).
    """
    try:
        name = payload.name.strip()
        email = payload.email.lower().strip()
        role = payload.role.strip().lower()
        phone = payload.phone.strip() if payload.phone and payload.phone.strip() else None

        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name is required")

        if len(payload.password.strip()) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

        if role not in {"farmer", "officer", "admin"}:
            raise HTTPException(status_code=400, detail="Role is required")

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            logger.warning("Registration attempt with existing email: %s", email)
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(
            name=name,
            phone=phone,
            email=email,
            district=(payload.district.strip() if payload.district and payload.district.strip() else None),
            taluk=(payload.taluk.strip() if payload.taluk and payload.taluk.strip() else None),
            language=payload.language,
            role=role,
            hashed_password=hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info("New user registered: %s (%s)", user.email, user.role)

        return token_response(user)

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        message = str(e.orig).lower() if getattr(e, "orig", None) else str(e).lower()
        if "users.email" in message or "email" in message:
            raise HTTPException(status_code=409, detail="Email already registered")
        logger.exception("Registration integrity error")
        raise HTTPException(status_code=400, detail="Registration details could not be saved. Please check the form and try again.")
    except Exception as e:
        db.rollback()
        logger.exception("Registration error")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email, password, and optional selected role.
    """
    try:
        email = payload.email.lower().strip()
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.warning("Login attempt for missing account: %s", email)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found. Please register first.")

        if not verify_password(payload.password, user.hashed_password):
            logger.warning("Incorrect password for %s", email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")

        if payload.role and user.role != payload.role:
            logger.warning("Role mismatch during login for %s", email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Selected role does not match this account.")

        logger.info("User logged in: %s (%s)", user.email, user.role)

        return token_response(user)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Login error")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/google", response_model=TokenResponse)
def google_login():
    """
    Google OAuth is intentionally disabled until token verification is implemented.
    """
    logger.info("Google login requested but not implemented")
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is coming soon")

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    """
    List registered users for the admin panel without exposing password hashes.
    """
    try:
        return db.query(User).order_by(User.created_at.desc()).all()
    except Exception:
        logger.exception("Error fetching registered users")
        raise HTTPException(status_code=500, detail="Failed to fetch registered users")

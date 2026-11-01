import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

# database must be imported first: it loads the .env file
from backend.app.database import engine
from backend.app.email_service import email_status, send_otp_email
from backend.app.models import PendingRegistration, User

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not found in .env file")

JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7
OTP_EXPIRE_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


# ---------- request bodies ----------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class EmailRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- helpers ----------

def now_utc():
    return datetime.now(timezone.utc)


def as_utc(value: datetime):
    # some DBs return naive datetimes; treat them as UTC
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode()[:72], password_hash.encode())


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email: str, otp: str) -> str:
    # never store the raw OTP
    return hmac.new(SECRET_KEY.encode(), f"{email}:{otp}".encode(), hashlib.sha256).hexdigest()


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": now_utc() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def user_json(user: User):
    return {"id": user.id, "name": user.name, "email": user.email}


def issue_and_send_otp(session: Session, pending: PendingRegistration):
    otp = generate_otp()
    pending.otp_hash = hash_otp(pending.email, otp)
    pending.otp_expires_at = now_utc() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    pending.otp_sent_at = now_utc()
    pending.attempts = 0
    session.commit()

    try:
        send_otp_email(pending.email, pending.name, otp, OTP_EXPIRE_MINUTES)
    except Exception as error:
        print("OTP email failed:", error)
        raise HTTPException(
            status_code=502,
            detail="Could not send OTP email. Please try again in a moment."
        )
    else:
        print(f"OTP email sent to {pending.email}")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    """Use as a dependency to protect any route: user = Depends(get_current_user)"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    with Session(engine) as session:
        user = session.get(User, int(payload["sub"]))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        session.expunge(user)
        return user


# ---------- routes ----------

@router.post("/register")
def register(body: RegisterRequest):
    email = body.email.lower()

    with Session(engine) as session:
        if session.query(User).filter_by(email=email).first():
            raise HTTPException(status_code=409, detail="An account with this email already exists")

        pending = session.query(PendingRegistration).filter_by(email=email).first()

        if pending:
            elapsed = (now_utc() - as_utc(pending.otp_sent_at)).total_seconds()
            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(status_code=429, detail=f"Please wait {wait}s before requesting another OTP")
            pending.name = body.name.strip()
            pending.password_hash = hash_password(body.password)
        else:
            pending = PendingRegistration(
                name=body.name.strip(),
                email=email,
                password_hash=hash_password(body.password),
                otp_hash="",
                otp_expires_at=now_utc(),
                otp_sent_at=now_utc(),
                attempts=0,
            )
            session.add(pending)

        issue_and_send_otp(session, pending)

    return {
        "status": "otp_sent",
        "message": f"OTP sent to {email}",
        "expires_in_minutes": OTP_EXPIRE_MINUTES,
    }


@router.post("/resend-otp")
def resend_otp(body: EmailRequest):
    email = body.email.lower()

    with Session(engine) as session:
        pending = session.query(PendingRegistration).filter_by(email=email).first()
        if pending is None:
            raise HTTPException(status_code=404, detail="No pending signup for this email. Please register again.")

        elapsed = (now_utc() - as_utc(pending.otp_sent_at)).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(status_code=429, detail=f"Please wait {wait}s before requesting another OTP")

        issue_and_send_otp(session, pending)

    return {"status": "otp_sent", "message": f"New OTP sent to {email}"}


@router.post("/verify-otp")
def verify_otp(body: VerifyOtpRequest):
    email = body.email.lower()

    with Session(engine) as session:
        pending = session.query(PendingRegistration).filter_by(email=email).first()
        if pending is None:
            raise HTTPException(status_code=404, detail="No pending signup for this email. Please register again.")

        if pending.attempts >= OTP_MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many wrong attempts. Please resend a new OTP.")

        if now_utc() > as_utc(pending.otp_expires_at):
            raise HTTPException(status_code=400, detail="OTP expired. Please resend a new OTP.")

        if not hmac.compare_digest(pending.otp_hash, hash_otp(email, body.otp)):
            pending.attempts += 1
            session.commit()
            left = OTP_MAX_ATTEMPTS - pending.attempts
            raise HTTPException(status_code=400, detail=f"Incorrect OTP. {left} attempt(s) left.")

        # verified -> create the real account
        user = User(
            name=pending.name,
            email=pending.email,
            password_hash=pending.password_hash,
            created_at=now_utc(),
        )
        session.add(user)
        session.delete(pending)
        session.commit()
        session.refresh(user)

        return {"status": "success", "token": create_token(user), "user": user_json(user)}


@router.post("/login")
def login(body: LoginRequest):
    email = body.email.lower()

    with Session(engine) as session:
        user = session.query(User).filter_by(email=email).first()

        if user is None:
            if session.query(PendingRegistration).filter_by(email=email).first():
                raise HTTPException(status_code=403, detail="Email not verified yet. Please complete OTP verification.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if not check_password(body.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        return {"status": "success", "token": create_token(user), "user": user_json(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"status": "success", "user": user_json(user)}


@router.get("/email-check")
def email_check(authorization: str = Header(default=None)):
    """Admin check of the email setup. Needs: Authorization: Bearer <CRON_SECRET>"""
    cron_secret = os.getenv("CRON_SECRET")
    if not cron_secret or authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return email_status()

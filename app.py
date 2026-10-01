import hmac
import os
import re
import threading
import time
from pathlib import Path
from typing import List, Literal

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.sessions import SessionMiddleware

from mini_report.mini_report import generate_mini_report_pdf

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"


def load_users() -> dict:
    """USERS env var: 'alice:pass1,bob:pass2' (fixed logins, no database)."""
    users = {}
    for pair in os.getenv("USERS", "").split(","):
        if ":" in pair:
            name, pw = pair.split(":", 1)
            if name.strip() and pw:
                users[name.strip()] = pw
    return users


USERS = load_users()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-only-change-me"),
    https_only=os.getenv("INSECURE_COOKIES") != "1",  # set to 1 only for local http testing
    same_site="lax",
    max_age=60 * 60 * 12,
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# One Chromium at a time keeps memory low on the free tier.
_pdf_lock = threading.Semaphore(1)


# ------------------------------
# Login
# ------------------------------
def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("user"))


@app.get("/login")
def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(FRONTEND_DIR / "login.html")


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    expected = USERS.get(username.strip())
    ok = expected is not None and hmac.compare_digest(expected.encode(), password.encode())
    if not ok:
        time.sleep(1)  # slow down password guessing
        return RedirectResponse("/login?error=1", status_code=303)
    request.session["user"] = username.strip()
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ------------------------------
# Report form + generation
# ------------------------------
@app.get("/")
def home(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(FRONTEND_DIR / "index.html")


class MonthRow(BaseModel):
    kwh: float = Field(ge=0, le=100000)
    bill: float = Field(ge=0, le=10000000)


class ReportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=300)
    ivrs: str
    meter_type: Literal["Single-phase", "Three-phase"]
    roof_area_sqft: float = Field(gt=0, le=1000000)
    months: List[MonthRow] = Field(min_length=3, max_length=12)

    @field_validator("ivrs")
    @classmethod
    def clean_ivrs(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{8,15}", v):
            raise ValueError("IVRS must be 8-15 letters/digits")
        return v

    @field_validator("name", "address")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("required")
        return v


def require_login(request: Request):
    if not is_logged_in(request):
        raise HTTPException(status_code=401, detail="Please log in again.")


@app.post("/api/generate", dependencies=[Depends(require_login)])
def generate(body: ReportRequest):
    if sum(m.kwh for m in body.months) <= 0 or sum(m.bill for m in body.months) <= 0:
        raise HTTPException(status_code=422, detail="Units and bill amounts cannot all be zero.")

    with _pdf_lock:
        try:
            pdf = generate_mini_report_pdf(
                ivrs=body.ivrs,
                name=body.name,
                address=body.address,
                meter_type=body.meter_type,
                roof_sqft=body.roof_area_sqft,
                monthly=[m.model_dump() for m in body.months],
            )
        except Exception as e:
            print("Report generation failed:", repr(e))
            raise HTTPException(status_code=500, detail="Could not generate the report. Please try again.")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{body.ivrs}_mini_report.pdf"'},
    )

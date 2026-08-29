import json

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from config import (
    API_SECRET,
    CORS_ORIGINS,
)

from db import (
    get_report,
    init_db,
)


init_db()

app = FastAPI(
    title="OSINT Core API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        CORS_ORIGINS
        if CORS_ORIGINS
        else ["*"]
    ),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "OSINT Core API",
    }


@app.get("/report/{token}")
async def report(
    token: str,
    x_secret: str | None = Header(
        default=None
    ),
):
    if (
        API_SECRET
        and x_secret != API_SECRET
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    row = get_report(
        token
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail=(
                "Report not found "
                "or expired"
            ),
        )

    return json.loads(
        row["payload"]
    )

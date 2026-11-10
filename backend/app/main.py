from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.upload import router as upload_router
from app.api.v1.review import router as review_router
from app.db.database import init_db
from app.core.config import settings
from app.core.errors import register_exception_handlers

@asynccontextmanager
async def lifespan(_app):
    init_db()  # create SQLite tables on startup
    yield

app = FastAPI(title="DocuSense AI API", version="0.2.0",
              description="Document ingestion, contradiction scan, persistence and audit API.",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"],
                   allow_headers=["*"])
register_exception_handlers(app)
app.include_router(upload_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "docusense-api", "version": app.version}

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "DocuSense AI API is running", "docs": "/docs"}

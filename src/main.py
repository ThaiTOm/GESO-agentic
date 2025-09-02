import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings
from utils.logging_config import *
from routes import rag_routes
from database.typesense_declare import get_typesense_instance_service
get_typesense_instance_service()
app = FastAPI(
    title="RAG PDF/Excel System API",
    description="API for the RAG system that processes PDFs and Excel files",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Mount static files for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


app.include_router(rag_routes.router, prefix="/api/v1", tags=["RAG System"])

# You can add a root endpoint for health checks
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "Welcome to the RAG API"}
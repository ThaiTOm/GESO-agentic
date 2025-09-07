import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from utils.logging_config import *
from routes import rag_routes, analysis_routes, rag_query_routes
from database.typesense_declare import get_typesense_instance_service

# Initialize Typesense
get_typesense_instance_service()

app = FastAPI(
    title="RAG and Data Analysis API",
    description="API for RAG system and Business Performance Trend Analysis",
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

# Add logging middleware (assuming you have this file)
app.add_middleware(LoggingMiddleware)

# Mount static files for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include your API routers
app.include_router(rag_routes.router, prefix="/api/v1", tags=["RAG System"])
app.include_router(analysis_routes.router, prefix="/api/v1", tags=["Data Analysis"])

app.include_router(rag_query_routes.router, prefix="/api/v1", tags=["RAG query System"])


# You can add a root endpoint for health checks
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "Welcome to the RAG and Data Analysis API"}
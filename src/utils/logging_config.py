import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any

# Import from starlette for middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request # Use Starlette's Request for middleware
from starlette.responses import Response # Use Starlette's Response for middleware
from starlette.types import ASGIApp # For type hinting in __init__

from config import settings

# Define log levels based on environment
def get_log_level() -> int:
    """Get the appropriate log level based on environment settings."""
    log_level = settings.LOG_LEVEL.upper()
    if log_level == "DEBUG":
        return logging.DEBUG
    elif log_level == "INFO":
        return logging.INFO
    elif log_level == "WARNING":
        return logging.WARNING
    elif log_level == "ERROR":
        return logging.ERROR
    elif log_level == "CRITICAL":
        return logging.CRITICAL
    else:
        # Default to INFO if invalid level
        return logging.INFO

# Configure logging formats
CONSOLE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
FILE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.abspath(settings.LOG_DIR)
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
APP_LOG_FILE = os.path.join(LOGS_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "error.log")
ACCESS_LOG_FILE = os.path.join(LOGS_DIR, "access.log")
PERFORMANCE_LOG_FILE = os.path.join(LOGS_DIR, "performance.log")

def setup_logger(name: str, log_file: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """
    Set up a logger with the specified name, log file, and level.

    Args:
        name: The name of the logger
        log_file: The file to log to (optional)
        level: The log level (optional, defaults to the level from settings)

    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)

    # Set the log level
    if level is None:
        level = get_log_level()
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # Create file handler if log_file is specified and file logging is enabled
    if log_file and settings.LOG_TO_FILE:
        max_bytes = settings.LOG_FILE_MAX_SIZE_MB * 1024 * 1024
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=settings.LOG_FILE_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    return logger

# Create default loggers
app_logger = setup_logger("app", APP_LOG_FILE)
error_logger = setup_logger("error", ERROR_LOG_FILE, logging.ERROR)
access_logger = setup_logger("access", ACCESS_LOG_FILE)
performance_logger = setup_logger("performance", PERFORMANCE_LOG_FILE)

def log_request(request_data: Dict[str, Any], endpoint: str) -> None:
    """
    Log API request details. (This function isn't directly used by the middleware below,
    but kept for other potential uses)
    """
    access_logger.info(f"Request to {endpoint}: {request_data}")

def log_response(response_data: Dict[str, Any], endpoint: str, status_code: int) -> None:
    """
    Log API response details. (This function isn't directly used by the middleware below,
    but kept for other potential uses)
    """
    if isinstance(response_data, dict) and "answer" in response_data:
        response_data["answer"] = response_data["answer"][:100] + "..." if len(response_data["answer"]) > 100 else response_data["answer"]
    access_logger.info(f"Response from {endpoint} (status {status_code}): {response_data}")

def log_error(error: Exception, context: str) -> None:
    """Log an error with context."""
    error_logger.error(f"Error in {context}: {str(error)}", exc_info=True)

def log_performance(operation: str, duration_ms: float) -> None:
    """Log performance metrics."""
    if settings.ENABLE_PERFORMANCE_MONITORING:
        performance_logger.info(f"{operation}|{duration_ms:.2f}")
        app_logger.info(f"Performance: {operation} took {duration_ms:.2f}ms")

# Setup middleware for FastAPI to log requests and responses
class LoggingMiddleware(BaseHTTPMiddleware): # Inherit from BaseHTTPMiddleware
    """Middleware for logging FastAPI requests and responses."""

    def __init__(self, app: ASGIApp): # Constructor now accepts app
        super().__init__(app)
        # You can add any one-time initialization here if needed
        app_logger.info("LoggingMiddleware initialized.")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process the request and log details.
        This method replaces the old __call__ method for BaseHTTPMiddleware.
        """
        # Skip logging if request logging is disabled
        if not settings.ENABLE_REQUEST_LOGGING:
            return await call_next(request)

        start_time = datetime.now()

        # Process the request and get the response
        try:
            response = await call_next(request) # This calls the next middleware or the route handler

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds() * 1000

            # Log the request details
            access_logger.info(
                f"Request: {request.method} {request.url.path} - "
                f"Client: {request.client.host if request.client else 'Unknown'} - " # Added client IP
                f"Status: {response.status_code} - "
                f"Duration: {duration:.2f}ms"
            )

            # Log performance metrics
            if settings.ENABLE_PERFORMANCE_MONITORING:
                endpoint = request.url.path
                performance_logger.info(f"endpoint:{endpoint}|method:{request.method}|status:{response.status_code}|duration:{duration:.2f}")

            return response
        except Exception as e:
            # Log any exceptions that occur during request processing by subsequent middleware/routes
            error_logger.error(
                f"Error processing request {request.method} {request.url.path}: {str(e)}",
                exc_info=True
            )
            # Re-raise the exception so FastAPI's error handling can take over
            # Or return a generic error response:
            # return Response("Internal Server Error", status_code=500)
            raise
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from routers import strategies
import logging
from auth_middleware import configure_auth, get_current_user, has_role
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with metadata
app = FastAPI(
    title="Strategy Service",
    description="API for managing trading strategies with authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure auth middleware
logger.info("Configuring authentication middleware")
try:
    configure_auth(app)
    logger.info("Authentication middleware configured successfully")
except Exception as e:
    logger.error(f"Failed to configure authentication middleware: {str(e)}")

# Include routers
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])

@app.get("/health")
async def health_check():
    """Health check endpoint that does not require authentication."""
    return {"status": "healthy"}

# Custom OpenAPI schema with security information
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"] = {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter JWT token. You can get token from /auth/login endpoint."
            }
        }
    }
    
    # Add security requirement to all endpoints except health
    for path in openapi_schema["paths"]:
        if path != "/health":
            for method in openapi_schema["paths"][path]:
                # Add security requirement
                openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]
                
                # Add response examples for auth errors
                if "responses" not in openapi_schema["paths"][path][method]:
                    openapi_schema["paths"][path][method]["responses"] = {}
                    
                # Add 401 response
                openapi_schema["paths"][path][method]["responses"]["401"] = {
                    "description": "Unauthorized - Missing or invalid token",
                    "content": {
                        "application/json": {
                            "example": {"detail": "Invalid authentication credentials"}
                        }
                    }
                }
                
                # Add 403 response for protected endpoints
                if "/activate" in path or "/deactivate" in path or method == "post" or method == "put" or method == "delete":
                    openapi_schema["paths"][path][method]["responses"]["403"] = {
                        "description": "Forbidden - Insufficient permissions",
                        "content": {
                            "application/json": {
                                "example": {"detail": "Not enough permissions"}
                            }
                        }
                    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
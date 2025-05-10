from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Cryptobot API",
        version="1.0.0",
        description="""API documentation for Cryptobot trading strategies.
        
        ## Authentication
        Most endpoints require authentication via JWT token.
        Obtain a token by logging in at `/token` endpoint.
        
        ## Versioning
        API version can be specified in the `Accept` header:
        `Accept: application/json; version=1.0`
        """,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"] = {
        "securitySchemes": {
            "OAuth2PasswordBearer": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "token",
                        "scopes": {}
                    }
                }
            }
        }
    }

    # Mark all operations as requiring auth by default
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"OAuth2PasswordBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

def setup_docs(app: FastAPI):
    """Configure API documentation settings"""
    app.openapi = lambda: custom_openapi(app)
    
    # Enable CORS for docs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
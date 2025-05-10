from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .exchanges import ExchangeRouter
from .errors import handle_exchange_errors

app = FastAPI(title="Exchange Gateway MCP")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include exchange routes
app.include_router(
    ExchangeRouter(),
    prefix="/api/exchanges",
    tags=["exchanges"]
)

# Add error handlers
app.exception_handler(Exception)(handle_exchange_errors)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
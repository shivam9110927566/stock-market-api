from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.endpoints import stock_api
from app.database.session import engine
from app.models.base import Base

# Modern Lifespan Event Handler (replaces deprecated @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Database tables create karna
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown logic (agar zaroorat ho)

app = FastAPI(
    title="Stock Market API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware (Taaki koi bhi frontend app aapki API ko bina error ke call kar sake)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production mein yahan specific domain de sakte hain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router include karein
app.include_router(stock_api.router, prefix="/api/v1", tags=["Stock API"])

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Welcome to Stock Market API. Visit /docs for documentation."
    }

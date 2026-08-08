import secrets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Startup & Shutdown Lifespan Handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Application startup...")
    yield
    # Shutdown logic
    print("Application shutdown...")

app = FastAPI(
    title="Stock Market API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware (Taaki frontend se connect ho sake)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Welcome to Stock Market API. Visit /docs for documentation."
    }

# 🔑 Yeh naya API Key generate karne ka option hai
@app.post("/generate-key")
def generate_api_key(username: str):
    # Ek secure random API key generate karna
    api_key = f"stock_key_{secrets.token_hex(12)}"
    return {
        "user": username,
        "api_key": api_key,
        "status": "Success! Aapki API key ban gayi hai."
    }

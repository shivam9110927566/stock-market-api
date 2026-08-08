from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Agar aapne database tables auto-create karne hain, toh unhe direct import karenge:
# (Agar abhi database file ready nahi hai, toh ye lifespan hata bhi sakte hain)
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

# Yahan aap apne baaki ke API routes/endpoints seedha likh sakte hain

import secrets
import yfinance as yf
from fastapi import FastAPI, HTTPException, Header
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

# 🔑 API Key generate karne ka option
@app.post("/generate-key")
def generate_api_key(username: str):
    # Ek secure random API key generate karna
    api_key = f"stock_key_{secrets.token_hex(12)}"
    return {
        "user": username,
        "api_key": api_key,
        "status": "Success! Aapki API key ban gayi hai."
    }

# 📈 Indian Stock Market Live Price check karne ka route (Smart Secured)
@app.get("/stock/{ticker}")
def get_stock_price(ticker: str, x_api_key: str = Header(...)):
    # Agar key 'stock_key_' se shuru hoti hai, toh access mil jayega
    if not x_api_key.startswith("stock_key_"):
        raise HTTPException(status_code=401, detail="Unauthorized! Galat API key hai bhai.")
    
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock data nahi mila. Sahi ticker daalein (jaise RELIANCE.NS).")
        
        current_price = data['Close'].iloc[-1]
        
        return {
            "ticker": ticker.upper(),
            "current_price": round(float(current_price), 2),
            "currency": "INR",
            "market": "NSE (India)",
            "status": "Success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

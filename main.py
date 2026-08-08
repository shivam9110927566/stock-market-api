import secrets
import yfinance as yf
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from cachetools import cached, TTLCache

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

# 🚀 Cache memory: Ek stock ka price 60 seconds tak save rahega (Rate limit se bachne ke liye)
stock_cache = TTLCache(maxsize=100, ttl=60)

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

# Yahoo Finance se data laane ka cached function
@cached(stock_cache)
def fetch_stock_data(ticker: str):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")
    if data.empty:
        return None
    return float(data['Close'].iloc[-1])

# 📈 Indian Stock Market Live Price check karne ka route (Smart Secured + Cached)
@app.get("/stock/{ticker}")
def get_stock_price(ticker: str, x_api_key: str = Header(...)):
    # Agar key 'stock_key_' se shuru hoti hai, toh access mil jayega
    if not x_api_key.startswith("stock_key_"):
        raise HTTPException(status_code=401, detail="Unauthorized! Galat API key hai bhai.")
    
    try:
        clean_ticker = ticker.upper()
        current_price = fetch_stock_data(clean_ticker)
        
        if current_price is None:
            raise HTTPException(status_code=404, detail="Stock data nahi mila. Sahi ticker daalein (jaise RELIANCE.NS).")
        
        return {
            "ticker": clean_ticker,
            "current_price": round(current_price, 2),
            "currency": "INR",
            "market": "NSE (India)",
            "status": "Success (Cached)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
